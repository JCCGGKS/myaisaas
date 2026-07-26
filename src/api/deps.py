"""API 依赖：DB session + 当前游客/用户解析（双 cookie 分桶，含写回 guest cookie）。"""
from fastapi import Depends, Request, Response

from business.identity import AUTH_COOKIE_NAME, GUEST_COOKIE_NAME, resolve_user
from config.settings import settings
from data.engine import get_session
from model.user import User


def get_db():
    yield from get_session()


def get_current_user(request: Request, response: Response, db=Depends(get_db)) -> User:
    auth_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    guest_cookie = request.cookies.get(GUEST_COOKIE_NAME)
    user, need_guest_cookie = resolve_user(db, auth_cookie, guest_cookie)
    if need_guest_cookie:
        # 首次游客：把匿名 ID 写回 guest cookie，后续请求复用同一游客
        response.set_cookie(
            GUEST_COOKIE_NAME,
            user.device_id,
            httponly=True,
            secure=settings.auth.cookie_secure,
            max_age=60 * 60 * 24 * 365,
            samesite="lax",
        )
    return user
