"""游客身份识别：从 cookie 解析当前用户（双 cookie 分桶）。

- 登录态：`wa_auth` 存 JWT（由 utils.security 签发），解析出真实用户；
- 游客态：`wa_guest` 存不透明随机串（匿名 ID），据此 upsert 游客用户；
- 两者分开存储，互不干扰：JWT 失效不会"降级"成游客，伪造的 auth cookie 不会
  凭空生成游客账号（详见 docs/01_guest.md）。
"""
import secrets

from data.engine import Session
from dao.user_dao import get_by_id, upsert_guest
from model.user import User
from utils.logging import get_logger
from utils.security import verify_token

logger = get_logger(__name__)

# 登录态 cookie（高价值凭证）：HttpOnly + Secure + SameSite=Strict
AUTH_COOKIE_NAME = "wa_auth"
# 游客标识 cookie（低价值）：HttpOnly + Secure + SameSite=Lax
GUEST_COOKIE_NAME = "wa_guest"


def new_anon_id() -> str:
    """生成游客用的不透明随机匿名 ID（加密随机，不可枚举）。"""
    return secrets.token_urlsafe(24)


def resolve_user(
    db: Session, auth_cookie: str | None, guest_cookie: str | None
) -> tuple[User, bool]:
    """解析当前用户，返回 (user, need_guest_cookie)。

    - 优先认登录态：auth cookie 是合法 JWT 且用户存在 → 返回登录用户；
      否则（无 cookie / JWT 失效）直接视为「未登录」，不降级成游客。
    - 游客分支：读独立的 guest cookie；缺失则生成新的匿名 ID 并标记需写回。
    """
    if auth_cookie:
        uid = verify_token(auth_cookie)
        if uid is not None:
            user = get_by_id(db, uid)
            if user is not None:
                return user, False
        # auth cookie 存在但无效 → 视为未登录，绝不当作游客

    # 游客分支：独立的 guest cookie
    if not guest_cookie:
        guest_cookie = new_anon_id()
        need_set = True
    else:
        need_set = False
    user = upsert_guest(db, guest_cookie)
    return user, need_set
