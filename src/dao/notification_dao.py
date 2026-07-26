"""Notification 数据访问：已推送记录，防重发。"""
from sqlalchemy import select

from data.engine import Session
from model.notification import Notification
from utils.logging import get_logger

logger = get_logger(__name__)


def record(db: Session, event_id: int, channel: str, recipient: str | None) -> Notification:
    n = Notification(event_id=event_id, channel=channel, recipient=recipient)
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def exists(db: Session, event_id: int, channel: str) -> bool:
    return (
        db.scalar(
            select(Notification.id).where(
                Notification.event_id == event_id, Notification.channel == channel
            )
        )
        is not None
    )
