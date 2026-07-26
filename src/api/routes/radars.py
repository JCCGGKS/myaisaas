"""雷达路由：创建（LLM 解析）/ 列表 / 详情 / 暂停恢复 / 多通道 / 事件流。"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Response

from api.deps import get_current_user, get_db
from business.radar_service import (
    create_radar,
    delete_radar,
    get_radar,
    list_radars,
    pause_radar,
    resume_radar,
    set_radar_channels,
)
from dao.event_dao import list_by_radar
from model.user import User
from schema.dtos import EventOut, RadarChannelsIn, RadarCreate, RadarOut

router = APIRouter(prefix="/api/radars", tags=["radars"])


@router.post("", response_model=RadarOut, status_code=201)
async def create(payload: RadarCreate, response: Response, user: User = Depends(get_current_user), db=Depends(get_db)):
    radar = await create_radar(db, user, payload.raw_query, payload.notify_channels)
    return RadarOut.model_validate(radar)


@router.get("", response_model=list[RadarOut])
async def list_mine(user: User = Depends(get_current_user), db=Depends(get_db)):
    return [RadarOut.model_validate(r) for r in list_radars(db, user)]


@router.get("/{radar_id}", response_model=RadarOut)
async def detail(radar_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    return RadarOut.model_validate(get_radar(db, user, radar_id))


@router.put("/{radar_id}/channels", response_model=RadarOut)
async def set_channels(radar_id: int, payload: RadarChannelsIn, user: User = Depends(get_current_user), db=Depends(get_db)):
    radar = set_radar_channels(db, user, radar_id, payload.notify_channels)
    return RadarOut.model_validate(radar)


@router.post("/{radar_id}/pause", response_model=RadarOut)
async def pause(radar_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    return RadarOut.model_validate(pause_radar(db, user, radar_id))


@router.post("/{radar_id}/resume", response_model=RadarOut)
async def resume(radar_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    return RadarOut.model_validate(resume_radar(db, user, radar_id))


@router.delete("/{radar_id}", status_code=200)
async def delete(radar_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    delete_radar(db, user, radar_id)
    return {"ok": True}


@router.get("/{radar_id}/events", response_model=list[EventOut])
async def list_events(
    radar_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
    since: datetime | None = Query(None),
    unread: bool = Query(False),
    limit: int = Query(50),
):
    get_radar(db, user, radar_id)  # 鉴权：确保归属
    return [EventOut.model_validate(e) for e in list_by_radar(db, radar_id, since=since, unread_only=unread, limit=limit)]
