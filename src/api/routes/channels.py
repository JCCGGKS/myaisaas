"""渠道路由（渠道无关）：列出可用渠道 + 绑定 + 邮箱验证。"""
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import JSONResponse

from api.deps import get_current_user, get_db
from business.channel_service import bind_channel, list_channels, verify_channel
from model.user import User
from schema.dtos import ChannelBind, ChannelOut

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("", response_model=list[ChannelOut])
async def list_mine(user: User = Depends(get_current_user), db=Depends(get_db)):
    return list_channels(db, user)


@router.post("/{channel_type}/bind", response_model=ChannelOut)
async def bind(
    channel_type: str,
    payload: Optional[ChannelBind] = Body(default=None),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    recipient = payload.recipient if payload else ""
    # bind_channel 现含验证邮件发送（异步），需 await
    result = await bind_channel(db, user, channel_type, recipient)
    return JSONResponse(result)


@router.get("/verify")
async def verify(
    token: str = Query(...),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """邮箱验证：用户点邮件链接后访问，凭一次性令牌置 verified。"""
    ok = await verify_channel(db, user, token)
    return {"ok": ok}
