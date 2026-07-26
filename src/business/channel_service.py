"""渠道业务：列出可用渠道与绑定状态；绑定（含游客限额）。

渠道无关：不写死 telegram。telegram 绑定返回 connect_url，由 bot webhook 回填 chat_id。
"""
from data.engine import Session
from dao.channel_dao import bind, count_bound, is_bound, list_bindings, update_recipient
from dao.radar_dao import backfill_notify_channel
from config.settings import settings
from model.user import User
from utils.exceptions import AppError, LimitExceededError
from utils.logging import get_logger

logger = get_logger(__name__)


def _normalize(channel_type: str) -> str:
    ct = (channel_type or "").strip().lower()
    if ct == "webhook":
        return "webhook"
    return ct


def list_channels(db: Session, user: User) -> list[dict]:
    bindings = {b.get("channel_type"): b for b in list_bindings(db, user)}
    result = []
    for ct in ["telegram", "email", "webhook"]:
        b = bindings.get(ct)
        result.append(
            {"type": ct, "bound": b is not None, "verified": bool(b.get("verified")) if b else False}
        )
    return result


def bind_channel(db: Session, user: User, channel_type: str, recipient: str = "") -> dict:
    ct = _normalize(channel_type)
    if ct not in ("telegram", "email", "webhook"):
        raise AppError(f"unknown channel: {ct}", status_code=400, code="unknown_channel")

    # 已绑定同渠道：更新接收人（不计入新增限额）
    if is_bound(db, user, ct):
        if ct == "telegram":
            # telegram 重新获取 connect_url
            result = {"type": ct, "bound": True, "verified": False, "connect_url": _connect_url(user.id)}
        else:
            if recipient:
                update_recipient(db, user, ct, recipient)
            result = {"type": ct, "bound": True, "verified": True}
        backfill_notify_channel(db, user.id, ct)
        return result

    # 游客限额：绑定第一个后不能再绑第二个不同渠道
    if user.is_guest and count_bound(db, user) >= settings.guest_channel_limit:
        raise LimitExceededError("游客最多绑定 1 个渠道，登录解锁多渠道")

    if ct == "telegram":
        bind(db, user, ct, recipient="", verified=False)
        result = {"type": ct, "bound": True, "verified": False, "connect_url": _connect_url(user.id)}
        backfill_notify_channel(db, user.id, ct)
        return result

    if not recipient:
        raise AppError(f"channel {ct} 需要 recipient（地址/URL）", status_code=422, code="invalid_input")
    bind(db, user, ct, recipient=recipient, verified=True)
    result = {"type": ct, "bound": True, "verified": True}
    backfill_notify_channel(db, user.id, ct)
    return result


def _connect_url(user_id: int) -> str:
    # MVP 占位：真实场景返回 t.me/<bot>?start=<token>
    return f"/webhooks/telegram?user_id={user_id}"
