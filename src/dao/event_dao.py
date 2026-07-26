"""Event 数据访问：按雷达列事件。"""
from sqlalchemy import select

from data.engine import Session
from model.event import Event


def list_by_radar(db: Session, radar_id: int) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(Event.radar_id == radar_id)
            .order_by(Event.created_at.desc())
        )
    )
