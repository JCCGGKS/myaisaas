"""Webhook：Telegram bot 回调写回 chat_id（MVP 占位，真实场景由 Bot 平台推送）。"""
from fastapi import APIRouter, Depends

from api.deps import get_db
from dao.channel_dao import update_recipient
from dao.user_dao import get_by_id
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/telegram")
async def telegram_webhook(body: dict, db=Depends(get_db)):
    user_id = body.get("user_id")
    chat_id = body.get("chat_id")
    if not user_id or not chat_id:
        return {"ok": False, "error": "user_id and chat_id required"}
    user = get_by_id(db, int(user_id))
    if user is None:
        return {"ok": False, "error": "user not found"}
    update_recipient(db, user, "telegram", str(chat_id))
    return {"ok": True}
