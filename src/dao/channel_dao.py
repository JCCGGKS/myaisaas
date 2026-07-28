"""Channel 数据访问：操作 User.channel_bindings（渠道无关 JSON 列表）。

每条绑定：{channel_type, recipient, verified, bind_token?, bind_token_expire_at?, verified_at?}
- email：bind 时先建占位（verified=False, 带一次性 bind_token），验证邮件点链接后才 verified=True
- feishu：绑定即 verified（webhook 本身即凭证，无邮件验证环节）
- webpush：本期未实现（见 channel_service，返回 501）
"""
import time

from data.engine import Session
from model.user import User
from utils.logging import get_logger

logger = get_logger(__name__)

BIND_TOKEN_TTL = 30 * 60  # 验证令牌有效期（秒）


def list_bindings(db: Session, user: User) -> list[dict]:
    return list(user.channel_bindings or [])


def count_bound(db: Session, user: User) -> int:
    return len(user.channel_bindings or [])


def is_bound(db: Session, user: User, channel_type: str) -> bool:
    return any(b.get("channel_type") == channel_type for b in (user.channel_bindings or []))


def bind(
    db: Session,
    user: User,
    channel_type: str,
    recipient: str = "",
    verified: bool = True,
    bind_token: str | None = None,
    bind_token_expire_at: float | None = None,
) -> dict:
    # 用 dict(x) 浅拷贝，避免原地修改被 SQLAlchemy 的 JSON 比较器误判为未变更
    bindings = [dict(x) for x in (user.channel_bindings or [])]
    bindings.append(
        {
            "channel_type": channel_type,
            "recipient": recipient,
            "verified": verified,
            "bind_token": bind_token,
            "bind_token_expire_at": bind_token_expire_at,
            "verified_at": None,
        }
    )
    user.channel_bindings = bindings
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("绑定渠道 user_id=%s channel=%s recipient=%r", user.id, channel_type, recipient)
    return bindings[-1]


def update_recipient(
    db: Session,
    user: User,
    channel_type: str,
    recipient: str,
    bind_token: str | None = None,
    bind_token_expire_at: float | None = None,
) -> None:
    """重新绑定/重发验证：更新接收人 + 重置验证令牌。"""
    bindings = [dict(x) for x in (user.channel_bindings or [])]
    for b in bindings:
        if b.get("channel_type") == channel_type:
            b["recipient"] = recipient
            b["verified"] = False
            b["bind_token"] = bind_token
            b["bind_token_expire_at"] = bind_token_expire_at
            b["verified_at"] = None
    user.channel_bindings = bindings
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("更新渠道接收人 user_id=%s channel=%s", user.id, channel_type)


def verify_by_token(db: Session, user: User, token: str) -> bool:
    """凭一次性 bind_token 将对应绑定置为已验证；令牌无效/过期返回 False。"""
    bindings = [dict(x) for x in (user.channel_bindings or [])]
    for b in bindings:
        if b.get("bind_token") == token:
            if not token:
                return False
            expire = b.get("bind_token_expire_at")
            if expire is not None and time.time() > expire:
                logger.warning("渠道验证令牌过期 user_id=%s channel=%s", user.id, b.get("channel_type"))
                return False
            b["verified"] = True
            b["verified_at"] = time.time()
            b.pop("bind_token", None)
            b.pop("bind_token_expire_at", None)
            user.channel_bindings = bindings
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("渠道验证成功 user_id=%s channel=%s", user.id, b.get("channel_type"))
            return True
    logger.warning("渠道验证令牌不存在 user_id=%s", user.id)
    return False
