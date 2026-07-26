"""渠道业务：列出可用渠道与绑定状态；绑定（含游客限额 + 邮箱验证）。

渠道无关：不写死具体渠道。本期落地 `email`（本地 SMTP + 验证邮件）；
`webpush` / `feishu` 为后续扩展，绑定返回未实现。
"""
import json
import secrets
import time
from pathlib import Path

from data.engine import Session
from dao.channel_dao import (
    bind,
    count_bound,
    is_bound,
    list_bindings,
    update_recipient,
    verify_by_token,
)
from dao.radar_dao import append_channel_to_radars
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


def list_channels(db: Session, user: User) -> list[dict]:
    bindings = {b.get("channel_type"): b for b in list_bindings(db, user)}
    result = []
    for ct in CHANNEL_TYPES:
        b = bindings.get(ct)
        result.append(
            {"type": ct, "bound": b is not None, "verified": bool(b.get("verified")) if b else False}
        )
    return result


async def bind_channel(db: Session, user: User, channel_type: str, recipient: str = "") -> dict:
    ct = _normalize(channel_type)
    if ct not in CHANNEL_TYPES:
        raise AppError(f"unknown channel: {ct}", status_code=400, code="unknown_channel")

    # 游客限额：仅对新渠道生效（已绑定的重绑不计入）。优先于 not_implemented，
    # 这样已达限额的游客尝试任何新渠道都返回 limit_exceeded。
    if user.is_guest and count_bound(db, user) >= settings.guest_channel_limit and not is_bound(db, user, ct):
        raise LimitExceededError("游客最多绑定 1 个渠道，登录解锁多渠道")

    if ct in ("webpush", "feishu"):
        raise AppError(f"渠道 {ct} 尚未实现（后续扩展）", status_code=501, code="not_implemented")

    # ---- email 绑定：生成一次性令牌 + 发验证邮件，验证后才 verified ----
    address = _normalize_email(recipient)
    if not address or "@" not in address:
        raise AppError("email 需要合法的邮箱地址（或 QQ 号）", status_code=422, code="invalid_input")

    token = secrets.token_urlsafe(24)
    expire = time.time() + BIND_TOKEN_TTL
    if is_bound(db, user, "email"):
        # 重新绑定：更新接收人 + 重置验证令牌，重发验证邮件（不计入新增限额）
        update_recipient(db, user, "email", address, bind_token=token, bind_token_expire_at=expire)
    else:
        bind(db, user, "email", recipient=address, verified=False, bind_token=token,
             bind_token_expire_at=expire)
    await _send_verification_email(address, token)
    append_channel_to_radars(db, user.id, "email")
    return {"type": "email", "bound": True, "verified": False}


async def verify_channel(db: Session, user: User, token: str) -> bool:
    """凭一次性令牌验证邮箱归属；无效/过期返回 False。"""
    return verify_by_token(db, user, token)


async def _send_verification_email(address: str, token: str) -> None:
    link = f"{settings.backend_base_url}/api/channels/verify?token={token}"
    msg = PushMessage(
        title="确认绑定 Watch Anything 邮箱",
        body=f"点击以下链接完成邮箱验证（30 分钟内有效）：\n{link}",
        url=link,
    )
    channel = EmailChannel()
    ok = await channel.send(address, msg)
    if not ok:
        logger.warning("验证邮件发送失败 address=%s（用户仍需重试绑定）", address)
