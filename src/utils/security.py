"""轻量鉴权工具（MVP）：token = f"tok.{user_id}.{sig}"，HMAC 签名。

仅用于打通游客→登录流程，生产应替换为 JWT + 密码哈希。
"""
import hashlib
import hmac

from config.settings import settings


def _sign(user_id: int) -> str:
    msg = f"{user_id}".encode()
    sig = hmac.new(settings.secret_key.encode(), msg, hashlib.sha256).hexdigest()[:16]
    return f"tok.{user_id}.{sig}"


def issue_token(user_id: int) -> str:
    return _sign(user_id)


def verify_token(token: str) -> int | None:
    if not token or not token.startswith("tok."):
        return None
    try:
        _, uid_str, sig = token.split(".", 2)
        expected = _sign(int(uid_str)).split(".", 2)[2]
        if hmac.compare_digest(expected, sig):
            return int(uid_str)
    except (ValueError, AttributeError):
        return None
    return None
