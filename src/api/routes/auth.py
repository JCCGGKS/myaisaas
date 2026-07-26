"""鉴权路由：注册/登录（升级当前游客） + 当前用户 + 登出。"""
from fastapi import APIRouter, Depends, Response

from api.deps import AUTH_COOKIE_NAME, GUEST_COOKIE_NAME, get_current_user, get_db
from business.auth_service import upgrade_current_guest
from config.settings import settings
from model.user import User
from schema.dtos import AuthIn, AuthMeOut, AuthOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    """写入登录态 cookie：HttpOnly + Secure + SameSite=Strict（高价值凭证）。"""
    response.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.auth.cookie_secure,
        max_age=60 * 60 * 24 * 30,
        samesite="strict",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(AUTH_COOKIE_NAME, samesite="strict")


def _clear_guest_cookie(response: Response) -> None:
    """登录成功后清除游客 cookie，避免后续请求仍带旧游客标识。"""
    response.delete_cookie(GUEST_COOKIE_NAME, samesite="lax")


@router.post("/register", response_model=AuthOut)
async def register(payload: AuthIn, response: Response, user: User = Depends(get_current_user), db=Depends(get_db)):
    _, token = upgrade_current_guest(db, user, payload.email, payload.password, name=payload.name, require_existing=False)
    _set_auth_cookie(response, token)
    _clear_guest_cookie(response)
    return AuthOut(token=token, user_id=user.id, is_guest=False)


@router.post("/login", response_model=AuthOut)
async def login(payload: AuthIn, response: Response, user: User = Depends(get_current_user), db=Depends(get_db)):
    _, token = upgrade_current_guest(db, user, payload.email, payload.password, name=payload.name, require_existing=True)
    _set_auth_cookie(response, token)
    _clear_guest_cookie(response)
    return AuthOut(token=token, user_id=user.id, is_guest=False)


@router.get("/me", response_model=AuthMeOut)
async def me(user: User = Depends(get_current_user)):
    return AuthMeOut(
        user_id=user.id,
        email=user.email,
        name=user.name,
        is_guest=user.is_guest,
    )


@router.post("/logout")
async def logout(response: Response):
    _clear_auth_cookie(response)
    _clear_guest_cookie(response)
    return {"ok": True}
