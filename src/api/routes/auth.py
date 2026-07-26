"""鉴权路由：注册/登录（升级当前游客） + 当前用户 + 登出。"""
from fastapi import APIRouter, Depends, Response

from api.deps import COOKIE_NAME, get_current_user, get_db
from model.user import User
from schema.dtos import AuthIn, AuthMeOut, AuthOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, max_age=60 * 60 * 24 * 30, samesite="lax"
    )


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, samesite="lax")


@router.post("/register", response_model=AuthOut)
async def register(payload: AuthIn, response: Response, user: User = Depends(get_current_user), db=Depends(get_db)):
    from business.auth_service import upgrade_current_guest

    _, token = upgrade_current_guest(db, user, payload.email, payload.password, require_existing=False)
    _set_cookie(response, token)
    return AuthOut(token=token, user_id=user.id, is_guest=False)


@router.post("/login", response_model=AuthOut)
async def login(payload: AuthIn, response: Response, user: User = Depends(get_current_user), db=Depends(get_db)):
    from business.auth_service import upgrade_current_guest

    _, token = upgrade_current_guest(db, user, payload.email, payload.password, require_existing=True)
    _set_cookie(response, token)
    return AuthOut(token=token, user_id=user.id, is_guest=False)


@router.get("/me", response_model=AuthMeOut)
async def me(user: User = Depends(get_current_user)):
    return AuthMeOut(
        user_id=user.id,
        email=user.email,
        is_guest=user.is_guest,
        channel_bindings=user.channel_bindings or [],
    )


@router.post("/logout")
async def logout(response: Response):
    _clear_cookie(response)
    return {"ok": True}
