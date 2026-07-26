"""渠道路由（渠道无关）：列出可用渠道 + 绑定。"""
from typing import Optional

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse

from api.deps import get_current_user, get_db
from business.channel_service import bind_channel, list_channels
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
    result = bind_channel(db, user, channel_type, recipient)
    # telegram 绑定返回 connect_url，前端据此引导用户连接 bot
    return JSONResponse(result)
