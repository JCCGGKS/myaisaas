"""接收外部 push 源（webhook / RSS 回调）写入候选事件，进入打分→去重→推送流程。

MVP 简化：无需游客 cookie（外部系统调用），凭 radar_id 定位雷达与所属用户。
生产应加签名/密钥校验（TODO）。
"""
from fastapi import APIRouter, Body, Depends

from api.deps import get_db
from business.monitor.scanner import scan_items
from business.monitor.sources import WebhookSource
from dao.radar_dao import get
from dao.user_dao import get_by_id
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/{source_type}")
async def ingest(source_type: str, body: dict = Body(...), db=Depends(get_db)):
    radar_id = body.get("radar_id")
    payload = body.get("items") or []
    radar = get(db, int(radar_id)) if radar_id is not None else None
    if radar is None:
        return {"ok": False, "error": "radar not found"}
    user = get_by_id(db, radar.owner_id)
    if user is None:
        return {"ok": False, "error": "user not found"}
    raw_items = WebhookSource.from_payload(source_type, payload)
    pushed = await scan_items(db, radar, user, raw_items)
    logger.info("ingest source=%s radar=%s items=%d pushed=%s", source_type, radar_id, len(raw_items), pushed)
    return {"ok": True, "processed": len(raw_items), "pushed": pushed}
