"""鉴权工具（MVP）：JWT（HS256）+ 密码哈希（bcrypt）。

- 登录/注册后签发 JWT，写入 `wa_auth` cookie（HttpOnly + Secure + SameSite=Strict）；
- 游客标识存于独立的 `wa_guest` cookie（不透明随机串），与 JWT 分桶；
- 密码以 bcrypt 哈希存储，绝不存明文；
- 生产务必用环境变量 WA_SECRET_KEY 覆盖为随机长串。
"""
import datetime

import bcrypt
import jwt

from config.settings import settings

ALGORITHM = "HS256"


def issue_token(user_id: int, is_guest: bool = False) -> str:
    """签发 JWT，载荷 sub=user_id，exp 取自 settings.token_expire_hours。"""
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(hours=settings.token_expire_hours)
    payload = {
        "sub": str(user_id),
        "is_guest": bool(is_guest),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def verify_token(token: str) -> int | None:
    """校验 JWT，成功返回 user_id，失败返回 None。

    仅用于校验 `wa_auth` cookie 中的登录态；游客标识存于独立的 `wa_guest`
    cookie，不在此解析。校验失败一律返回 None，由上层判定为「未登录」。
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        return int(sub)
    except (jwt.PyJWTError, ValueError):
        return None


# ---------- 密码哈希（bcrypt，绝不存明文） ----------

def hash_password(password: str) -> str:
    """bcrypt 哈希，返回可存储的字符串（含 salt，约 60 字符）。"""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str | None) -> bool:
    """校验明文密码与存储哈希是否匹配；空哈希直接返回 False。"""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
