"""Radar 数据访问：建 / 列 / 计数（按 owner）。"""
from sqlalchemy import func, select, update

from data.engine import Session
from model.radar import Radar
from utils.logging import get_logger

logger = get_logger(__name__)


def create(db: Session, owner_id: int, raw_query: str, notify_channel: str = "telegram") -> Radar:
    radar = Radar(owner_id=owner_id, raw_query=raw_query, notify_channel=notify_channel)
    db.add(radar)
    db.commit()
    db.refresh(radar)
    logger.info("创建雷达 user_id=%s radar_id=%s query=%r", owner_id, radar.id, raw_query)
    return radar


def list_by_owner(db: Session, owner_id: int) -> list[Radar]:
    return list(db.scalars(select(Radar).where(Radar.owner_id == owner_id).order_by(Radar.created_at.desc())))


def count_by_owner(db: Session, owner_id: int) -> int:
    return db.scalar(select(func.count(Radar.id)).where(Radar.owner_id == owner_id)) or 0


def get(db: Session, radar_id: int) -> Radar | None:
    return db.get(Radar, radar_id)


def backfill_notify_channel(db: Session, owner_id: int, channel: str) -> None:
    """绑定渠道后，把该用户名下 notify_channel 为空的雷达回填成此渠道。"""
    db.execute(
        update(Radar)
        .where(Radar.owner_id == owner_id, Radar.notify_channel == "")
        .values(notify_channel=channel)
    )
    db.commit()
    logger.info("回填雷达推送渠道 owner_id=%s channel=%s", owner_id, channel)
