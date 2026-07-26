"""游客身份识别：从 cookie 解析当前用户。

- 登录后 cookie 为签名 token（tok.*），解析为真实用户；
- 否则 cookie 视为 device_id，upsert 一个游客用户。
"""
import uuid

from data.engine import Session
from dao.user_dao import get_by_id, upsert_guest
from utils.logging import get_logger
from utils.security import verify_token

logger = get_logger(__name__)

COOKIE_NAME = "wa_uid"
TOKEN_PREFIX = "tok."


def new_device_id() -> str:
    return f"dev_{uuid.uuid4().hex}"


def resolve_user(db: Session, cookie_value: str | None) -> tuple[object, bool]:
    """返回 (user, is_new_cookie)。is_new_cookie 表示需要写回新 cookie。"""
    if cookie_value and cookie_value.startswith(TOKEN_PREFIX):
        uid = verify_token(cookie_value)
        if uid is not None:
            user = get_by_id(db, uid)
            if user is not None:
                return user, False

    # 游客：用 cookie 作 device_id，无则生成
    device_id = cookie_value if (cookie_value and not cookie_value.startswith(TOKEN_PREFIX)) else new_device_id()
    user = upsert_guest(db, device_id)
    return user, True
