"""Webhook：Telegram bot 回调（暂未实现）。

渠道绑定现已「跟随雷达」存于 Radar.notify_channels，Telegram 绑定流程按既定计划延后
（先飞书），故本回调暂不可用，仅保留路由占位以便后续接入时直接实现，避免改动 main 注册。
"""
from fastapi import APIRouter, Depends, status

from api.deps import get_db
from utils.exceptions import AppError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/telegram")
async def telegram_webhook(body: dict, db=Depends(get_db)):
    raise AppError(
        "Telegram 绑定暂未实现（按计划先接入飞书），敬请期待",
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        code="not_implemented",
    )
