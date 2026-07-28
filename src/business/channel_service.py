"""渠道业务：列出可用渠道与绑定状态；绑定（含游客限额 + 邮箱验证）。

绑定跟随雷达：每个雷达独立持有自己的渠道绑定（含接收人），存于
`Radar.notify_channels`，不再存用户级、不再自动继承其他雷达。
本期落地 `email`（本地 SMTP + 验证邮件）、`feishu`（飞书群机器人 webhook 推送）；
`webpush` 为后续扩展，绑定返回未实现。
"""
import json
import secrets
import time
from pathlib import Path

from data.engine import Session
from dao.radar_dao import (
    get as get_radar,
    set_radar_binding,
    remove_radar_binding,
    find_radar_binding_by_token,
)
from config.settings import settings
from business.notifier.channels import EmailChannel, PushMessage
from model.user import User
from utils.exceptions import AppError, LimitExceededError
from utils.logging import get_logger

logger = get_logger(__name__)

BIND_TOKEN_TTL = 30 * 60  # 验证令牌有效期（秒）
_CHANNELS_JSON = Path(__file__).resolve().parents[2] / "etc" / "channels.json"
_FALLBACK_CHANNEL_TYPES = ["email", "webpush", "feishu"]


def _load_channel_types() -> list[str]:
    """从 etc/channels.json 加载可选渠道 type 列表；缺失/解析失败则回退内置清单。"""
    try:
        if not _CHANNELS_JSON.exists():
            logger.warning("渠道配置文件不存在 %s，回退内置清单 %s", _CHANNELS_JSON, _FALLBACK_CHANNEL_TYPES)
            return list(_FALLBACK_CHANNEL_TYPES)
        data = json.loads(_CHANNELS_JSON.read_text(encoding="utf-8"))
        types = [c["type"] for c in data.get("channels", []) if c.get("type")]
        if not types:
            logger.warning("渠道配置文件为空 %s，回退内置清单", _CHANNELS_JSON)
            return list(_FALLBACK_CHANNEL_TYPES)
        logger.info("从 %s 加载渠道清单：%s", _CHANNELS_JSON, types)
        return types
    except Exception as e:  # 配置异常不应阻断启动
        logger.error("读取渠道配置失败 %s：%s，回退内置清单", _CHANNELS_JSON, e)
        return list(_FALLBACK_CHANNEL_TYPES)


CHANNEL_TYPES = _load_channel_types()


def _normalize(channel_type: str) -> str:
    return (channel_type or "").strip().lower()


def _normalize_email(recipient: str) -> str:
    """QQ 号自动补 @qq.com；其余需含 @。"""
    r = (recipient or "").strip()
    if not r:
        return ""
    if "@" not in r and r.isdigit():
        return f"{r}@qq.com"
    return r


def _is_feishu_webhook(url: str) -> bool:
    """校验是否为飞书/飞书国际版群机器人 webhook 地址。"""
    if not url or not url.startswith("https://"):
        return False
    return "/open-apis/bot/v2/hook/" in url


def list_channels(db: Session, user: User, radar_id: int | None = None) -> list[dict]:
    """可选渠道目录（来自 etc/channels.json）。若传 radar_id，则按该雷达的实际绑定
    标注 bound / verified / recipient（绑定跟随雷达）。"""
    radar_bindings: dict = {}
    if radar_id is not None:
        radar = get_radar(db, radar_id)
        if radar is not None and radar.owner_id == user.id:
            radar_bindings = {
                b.get("channel_type"): b
                for b in (radar.notify_channels or [])
                if isinstance(b, dict)
            }
    result = []
    for ct in CHANNEL_TYPES:
        b = radar_bindings.get(ct)
        result.append(
            {
                "type": ct,
                "bound": b is not None,
                "verified": bool(b.get("verified")) if b else False,
                "recipient": b.get("recipient") if b else None,
            }
        )
    return result


async def bind_channel(
    db: Session, user: User, channel_type: str, recipient: str = "", radar_id: int | None = None
) -> dict:
    ct = _normalize(channel_type)
    if ct not in CHANNEL_TYPES:
        raise AppError(f"unknown channel: {ct}", status_code=400, code="unknown_channel")
    if radar_id is None:
        raise AppError("绑定需指定 radar_id（绑定跟随雷达）", status_code=422, code="invalid_input")

    radar = get_radar(db, radar_id)
    if radar is None or radar.owner_id != user.id or radar.deleted_at is not None:
        raise AppError("雷达不存在或无权限", status_code=404, code="not_found")

    existing = {
        b.get("channel_type"): b
        for b in (radar.notify_channels or [])
        if isinstance(b, dict)
    }
    already = ct in existing

    # 游客限额：按「单个雷达的绑定数」计；已绑定的重绑不计入新额度
    if user.is_guest and len(existing) >= settings.guest.channel_limit and not already:
        raise LimitExceededError("游客每个雷达最多绑定 1 个渠道，登录解锁多渠道")

    if ct == "webpush":
        raise AppError(f"渠道 {ct} 尚未实现（后续扩展）", status_code=501, code="not_implemented")

    # ---- feishu 绑定：群机器人 webhook 即凭证，绑定即 verified（无需邮件验证） ----
    if ct == "feishu":
        url = (recipient or "").strip()
        if not _is_feishu_webhook(url):
            raise AppError(
                "feishu 需要合法的群机器人 webhook 地址"
                "（形如 https://open.feishu.cn/open-apis/bot/v2/hook/xxxx）",
                status_code=422,
                code="invalid_input",
            )
        binding = {"channel_type": "feishu", "recipient": url, "verified": True}
        set_radar_binding(db, radar_id, binding)
        logger.info("feishu 绑定成功 radar_id=%s user_id=%s", radar_id, user.id)
        return {"type": "feishu", "bound": True, "verified": True}

    # ---- email 绑定：生成一次性令牌 + 发验证邮件，验证后才 verified ----
    address = _normalize_email(recipient)
    if not address or "@" not in address:
        raise AppError("email 需要合法的邮箱地址（或 QQ 号）", status_code=422, code="invalid_input")

    token = secrets.token_urlsafe(24)
    expire = time.time() + BIND_TOKEN_TTL
    binding = {
        "channel_type": "email",
        "recipient": address,
        "verified": False,
        "bind_token": token,
        "bind_token_expire_at": expire,
    }
    set_radar_binding(db, radar_id, binding)

    # 本地开发便捷：跳过「点击验证邮件」步骤，绑定即自动 verified。
    # 生产务必保留验证流程（settings.email.auto_verify=false），防垃圾推送。
    if settings.email.auto_verify:
        binding = {**binding, "verified": True}
        binding.pop("bind_token", None)
        binding.pop("bind_token_expire_at", None)
        set_radar_binding(db, radar_id, binding)
        logger.info("email 绑定自动验证（auto_verify=true，仅本地开发）radar_id=%s", radar_id)
        return {"type": "email", "bound": True, "verified": True}

    await _send_verification_email(address, token)
    return {"type": "email", "bound": True, "verified": False}


async def unbind_channel(db: Session, user: User, radar_id: int, channel_type: str) -> dict:
    ct = _normalize(channel_type)
    radar = get_radar(db, radar_id)
    if radar is None or radar.owner_id != user.id or radar.deleted_at is not None:
        raise AppError("雷达不存在或无权限", status_code=404, code="not_found")
    remove_radar_binding(db, radar_id, ct)
    logger.info("渠道解绑 radar_id=%s channel=%s", radar_id, ct)
    return {"type": ct, "bound": False, "verified": False}


async def verify_channel(db: Session, user: User, token: str) -> bool:
    """凭一次性令牌验证邮箱归属（令牌存于雷达绑定上）；无效/过期返回 False。"""
    return find_radar_binding_by_token(db, user, token) is not None


async def _send_verification_email(address: str, token: str) -> None:
    link = f"{settings.app.backend_base_url}/api/channels/verify?token={token}"
    msg = PushMessage(
        title="确认绑定 Watch Anything 邮箱",
        body=f"点击以下链接完成邮箱验证（30 分钟内有效）：\n{link}",
        url=link,
    )
    channel = EmailChannel()
    ok = await channel.send(address, msg)
    if not ok:
        logger.warning("验证邮件发送失败 address=%s（用户仍需重试绑定）", address)
