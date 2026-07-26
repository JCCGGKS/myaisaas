"""雷达路由。"""
from fastapi import APIRouter, Depends, Response

from api.deps import get_current_user, get_db
from business.radar_service import create_radar, list_radars
from dao.event_dao import list_by_radar
from model.user import User
from schema.dtos import EventOut, RadarCreate, RadarOut

router = APIRouter(prefix="/api/radars", tags=["radars"])


@router.post("", response_model=RadarOut, status_code=201)
async def create(payload: RadarCreate, response: Response, user: User = Depends(get_current_user), db=Depends(get_db)):
    radar = create_radar(db, user, payload.raw_query, payload.notify_channel)
    return RadarOut.model_validate(radar)


@router.get("", response_model=list[RadarOut])
async def list_mine(user: User = Depends(get_current_user), db=Depends(get_db)):
    return [RadarOut.model_validate(r) for r in list_radars(db, user)]


@router.get("/{radar_id}/events", response_model=list[EventOut])
async def list_events(radar_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    return [EventOut.model_validate(e) for e in list_by_radar(db, radar_id)]
