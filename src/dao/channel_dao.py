"""Channel 数据访问：操作 User.channel_bindings（渠道无关 JSON 列表）。

每条绑定：{channel_type, recipient, verified}
- email/webhook：直接提交 recipient，verified=True
- telegram：bind 时先建占位（recipient 空、verified=False），Webhook 回填 chat_id 并置 verified=True
"""
from data.engine import Session
from model.user import User
from utils.logging import get_logger

logger = get_logger(__name__)


def list_bindings(db: Session, user: User) -> list[dict]:
    return list(user.channel_bindings or [])


def count_bound(db: Session, user: User) -> int:
    return len(user.channel_bindings or [])


def is_bound(db: Session, user: User, channel_type: str) -> bool:
    return any(b.get("channel_type") == channel_type for b in (user.channel_bindings or []))


def bind(db: Session, user: User, channel_type: str, recipient: str = "", verified: bool = True) -> dict:
    # 用 dict(x) 浅拷贝，避免原地修改被 SQLAlchemy 的 JSON 比较器误判为未变更
    bindings = [dict(x) for x in (user.channel_bindings or [])]
    bindings.append({"channel_type": channel_type, "recipient": recipient, "verified": verified})
    user.channel_bindings = bindings
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("绑定渠道 user_id=%s channel=%s recipient=%r", user.id, channel_type, recipient)
    return bindings[-1]


def update_recipient(db: Session, user: User, channel_type: str, recipient: str) -> None:
    """Webhook 回填（telegram 拿到 chat_id 后）。"""
    bindings = [dict(x) for x in (user.channel_bindings or [])]
    for b in bindings:
        if b.get("channel_type") == channel_type:
            b["recipient"] = recipient
            b["verified"] = True
    user.channel_bindings = bindings
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("更新渠道接收人 user_id=%s channel=%s", user.id, channel_type)
