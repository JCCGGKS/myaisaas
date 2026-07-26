"""API 依赖：DB session + 当前游客/用户解析（含写回 cookie）。"""
from fastapi import Depends, Request, Response

from business.identity import COOKIE_NAME, resolve_user
from data.engine import get_session
from model.user import User


def get_db():
    yield from get_session()


def get_current_user(request: Request, response: Response, db=Depends(get_db)) -> User:
    cookie = request.cookies.get(COOKIE_NAME)
    user, need_cookie = resolve_user(db, cookie)
    if need_cookie:
        # 首次游客：把 device_id 写回 cookie，后续请求复用同一游客
        response.set_cookie(
            COOKIE_NAME,
            user.device_id,
            httponly=True,
            max_age=60 * 60 * 24 * 365,
            samesite="lax",
        )
    return user
