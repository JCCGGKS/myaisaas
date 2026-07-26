"""游客身份识别：从 cookie 解析当前用户。

- 登录后 cookie 为 JWT（由 utils.security 签发），解析出真实用户；
- 否则 cookie 视为 device_id（非 JWT），upsert 一个游客用户。
"""
import uuid

from data.engine import Session
from dao.user_dao import get_by_id, upsert_guest
from utils.logging import get_logger
from utils.security import verify_token

logger = get_logger(__name__)

COOKIE_NAME = "wa_uid"


def new_device_id() -> str:
    return f"dev_{uuid.uuid4().hex}"


def resolve_user(db: Session, cookie_value: str | None) -> tuple[object, bool]:
    """返回 (user, is_new_cookie)。is_new_cookie 表示需要写回新 cookie。"""
    if cookie_value:
        # 合法 JWT 解析出已注册用户；decode 失败（如游客 device_id）返回 None，走游客分支
        uid = verify_token(cookie_value)
        if uid is not None:
            user = get_by_id(db, uid)
            if user is not None:
                return user, False

    # 游客：cookie 作为 device_id（非 JWT），无则生成
    device_id = cookie_value or new_device_id()
    user = upsert_guest(db, device_id)
    return user, True
