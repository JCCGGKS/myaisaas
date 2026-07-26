"""Radar 数据访问：建 / 列 / 计数 / 扫描状态 / 渠道管理。"""
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from data.engine import Session
from model.radar import Radar
from utils.logging import get_logger

logger = get_logger(__name__)


def create(
    db: Session,
    owner_id: int,
    raw_query: str,
    notify_channels: list[str] | None = None,
    keywords: list | None = None,
    sources: list | None = None,
    filters: dict | None = None,
) -> Radar:
    radar = Radar(
        owner_id=owner_id,
        raw_query=raw_query,
        notify_channels=list(notify_channels or []),
        keywords=list(keywords or []),
        sources=list(sources or []),
        filters=dict(filters or {}),
    )
    db.add(radar)
    db.commit()
    db.refresh(radar)
    logger.info("创建雷达 user_id=%s radar_id=%s query=%r", owner_id, radar.id, raw_query)
    return radar


def list_by_owner(db: Session, owner_id: int) -> list[Radar]:
    return list(
        db.scalars(
            select(Radar).where(Radar.owner_id == owner_id, Radar.deleted_at.is_(None)).order_by(Radar.created_at.desc())
        )
    )


def count_by_owner(db: Session, owner_id: int) -> int:
    return db.scalar(select(func.count(Radar.id)).where(Radar.owner_id == owner_id, Radar.deleted_at.is_(None))) or 0


def get(db: Session, radar_id: int) -> Radar | None:
    return db.get(Radar, radar_id)


def get_active(db: Session) -> list[Radar]:
    """监控调度用：取所有未软删且 status=active 的雷达。"""
    return list(db.scalars(select(Radar).where(Radar.deleted_at.is_(None), Radar.status == "active")))


def set_channels(db: Session, radar_id: int, channels: list[str]) -> Radar | None:
    """PUT /radars/{id}/channels：直接设置该雷达的多通道列表。"""
    radar = get(db, radar_id)
    if radar is None:
        return None
    radar.notify_channels = list(dict.fromkeys(channels))  # 去重保序
    db.add(radar)
    db.commit()
    db.refresh(radar)
    logger.info("设置雷达渠道 radar_id=%s channels=%s", radar_id, radar.notify_channels)
    return radar


def append_channel_to_radars(db: Session, owner_id: int, channel: str) -> None:
    """账户绑定渠道后，把该渠道追加到用户名下所有雷达的 notify_channels（去重）。"""
    radars = list(db.scalars(select(Radar).where(Radar.owner_id == owner_id, Radar.deleted_at.is_(None))))
    for r in radars:
        if channel not in r.notify_channels:
            r.notify_channels = r.notify_channels + [channel]
            db.add(r)
    db.commit()
    logger.info("账户渠道回填雷达 owner_id=%s channel=%s", owner_id, channel)


def update_scan_state(
    db: Session,
    radar: Radar,
    scan_state: dict,
    last_scan_at=None,
    status: str | None = None,
    last_error: str | None = None,
) -> None:
    radar.scan_state = scan_state
    radar.last_scan_at = last_scan_at
    if status is not None:
        radar.status = status
    if last_error is not None:
        radar.last_error = last_error
    db.add(radar)
    db.commit()


def delete(db: Session, radar_id: int) -> Radar | None:
    """软删除：写入 deleted_at 标记，保留雷达及其事件/通知用于审计与误删恢复。

    所有读取查询（list_by_owner / get_active / get_radar）均按 deleted_at 过滤，
    因此软删后雷达在列表与详情中不可见、监控调度不再扫描，但数据仍可找回。
    """
    radar = db.get(Radar, radar_id)
    if radar is None:
        return None
    radar.deleted_at = datetime.now(timezone.utc)
    radar.active = False  # 保持与既有 active 语义一致，双重标记
    db.add(radar)
    db.commit()
    db.refresh(radar)
    logger.info("软删除雷达 radar_id=%s deleted_at=%s", radar_id, radar.deleted_at)
    return radar
