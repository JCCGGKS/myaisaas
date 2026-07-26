"""Event 数据访问：去重查询 / 创建 / 标记推送 / 列表（分页·过滤）。"""
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select

from data.engine import Session
from model.event import Event


def get_by_dedup_key(db: Session, radar_id: int, dedup_key: str) -> Event | None:
    return db.scalar(
        select(Event).where(Event.radar_id == radar_id, Event.dedup_key == dedup_key)
    )


def create(
    db: Session,
    radar_id: int,
    dedup_key: str,
    title: str,
    source_url: str | None,
    relevance_score: float | None,
    summary: str | None,
) -> Event:
    event = Event(
        radar_id=radar_id,
        dedup_key=dedup_key,
        title=title,
        source_url=source_url,
        relevance_score=relevance_score,
        summary=summary,
        pushed_channels=[],
        is_read=False,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def mark_pushed(db: Session, event: Event, channel: str) -> None:
    """记录某渠道已推送（防重发）。首次推送时写 pushed 时间。"""
    channels = list(event.pushed_channels or [])
    if channel not in channels:
        channels.append(channel)
    event.pushed_channels = channels
    if event.pushed is None:
        event.pushed = datetime.now(timezone.utc)
    db.add(event)
    db.commit()


def list_by_radar(
    db: Session,
    radar_id: int,
    *,
    since: datetime | None = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Event]:
    stmt = select(Event).where(Event.radar_id == radar_id)
    if since is not None:
        stmt = stmt.where(Event.created_at >= since)
    if unread_only:
        stmt = stmt.where(Event.is_read.is_(False))
    stmt = stmt.order_by(Event.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def exists_by_dedup_keys(db: Session, radar_id: int, keys: Iterable[str]) -> set[str]:
    """批量判断哪些 dedup_key 已存在（用于扫描去重）。"""
    keys = list(keys)
    if not keys:
        return set()
    rows = db.scalars(
        select(Event.dedup_key).where(Event.radar_id == radar_id, Event.dedup_key.in_(keys))
    ).all()
    return set(rows)
