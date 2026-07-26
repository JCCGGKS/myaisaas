"""鉴权路由：注册/登录（升级当前游客） + 合并。"""
from fastapi import APIRouter, Depends, Request, Response

from api.deps import COOKIE_NAME, get_current_user, get_db
from business.auth_service import upgrade_current_guest
from model.user import User
from schema.dtos import AuthIn, AuthOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, max_age=60 * 60 * 24 * 30, samesite="lax"
    )


@router.post("/register", response_model=AuthOut)
async def register(payload: AuthIn, response: Response, user: User = Depends(get_current_user), db=Depends(get_db)):
    _, token = upgrade_current_guest(db, user, payload.email, payload.password, require_existing=False)
    _set_cookie(response, token)
    return AuthOut(token=token, user_id=user.id, is_guest=False)


@router.post("/login", response_model=AuthOut)
async def login(payload: AuthIn, response: Response, user: User = Depends(get_current_user), db=Depends(get_db)):
    _, token = upgrade_current_guest(db, user, payload.email, payload.password, require_existing=True)
    _set_cookie(response, token)
    return AuthOut(token=token, user_id=user.id, is_guest=False)
