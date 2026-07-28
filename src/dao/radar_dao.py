"""Radar 数据访问：建 / 列 / 计数 / 扫描状态 / 渠道管理。"""
import time
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from data.engine import Session
from model.radar import Radar
from model.user import User
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


def set_channels(db: Session, radar_id: int, channels: list[dict]) -> Radar | None:
    """PUT /radars/{id}/channels：直接设置该雷达的多通道绑定列表（按 channel_type 去重保序）。"""
    radar = get(db, radar_id)
    if radar is None:
        return None
    seen = set()
    deduped = []
    for c in channels or []:
        ct = c.get("channel_type") if isinstance(c, dict) else c
        if ct in seen:
            continue
        seen.add(ct)
        deduped.append(c)
    radar.notify_channels = deduped
    db.add(radar)
    db.commit()
    db.refresh(radar)
    logger.info("设置雷达渠道 radar_id=%s channels=%s", radar_id, radar.notify_channels)
    return radar


def set_radar_binding(db: Session, radar_id: int, binding: dict) -> Radar | None:
    """按 channel_type 在该雷达的 notify_channels 中新增/覆盖一个绑定（绑定跟随雷达）。"""
    radar = get(db, radar_id)
    if radar is None:
        return None
    channels = list(radar.notify_channels or [])
    ct = binding.get("channel_type")
    for i, c in enumerate(channels):
        if isinstance(c, dict) and c.get("channel_type") == ct:
            channels[i] = binding
            break
    else:
        channels.append(binding)
    radar.notify_channels = channels
    db.add(radar)
    db.commit()
    db.refresh(radar)
    logger.info("雷达绑定渠道 radar_id=%s channel=%s", radar_id, ct)
    return radar


def remove_radar_binding(db: Session, radar_id: int, channel_type: str) -> Radar | None:
    """从某雷达解绑指定渠道。"""
    radar = get(db, radar_id)
    if radar is None:
        return None
    channels = [
        c for c in (radar.notify_channels or [])
        if not (isinstance(c, dict) and c.get("channel_type") == channel_type)
    ]
    radar.notify_channels = channels
    db.add(radar)
    db.commit()
    db.refresh(radar)
    logger.info("雷达解绑渠道 radar_id=%s channel=%s", radar_id, channel_type)
    return radar


def find_radar_binding_by_token(db: Session, user: User, token: str) -> int | None:
    """跨该用户所有雷达查找 bind_token；命中且未过期则置 verified，返回 radar_id。

    绑定已跟随雷达，故邮箱验证令牌存于雷达绑定上（不再存用户级）。

    注意：返写时必须为该绑定构造「全新 dict」再整体替换列表——
    SQLAlchemy 的 JSON 列对嵌套 dict 的就地修改可能不触发脏检测，导致写入丢失。
    """
    if not token:
        return None
    radars = list(db.scalars(select(Radar).where(Radar.owner_id == user.id, Radar.deleted_at.is_(None))))
    for radar in radars:
        channels = list(radar.notify_channels or [])
        new_channels = []
        hit = False
        for c in channels:
            if isinstance(c, dict) and c.get("bind_token") == token:
                if c.get("bind_token_expire_at") and time.time() > c["bind_token_expire_at"]:
                    logger.warning("雷达绑定验证令牌过期 radar=%s channel=%s", radar.id, c.get("channel_type"))
                    return None
                nc = dict(c)
                nc["verified"] = True
                nc["verified_at"] = time.time()
                nc.pop("bind_token", None)
                nc.pop("bind_token_expire_at", None)
                new_channels.append(nc)
                hit = True
            else:
                new_channels.append(c)
            if hit:
                radar.notify_channels = new_channels
                db.add(radar)
                db.commit()
                db.refresh(radar)
                logger.info("雷达绑定验证成功 radar=%s channel=%s", radar.id, nc.get("channel_type"))
                return radar.id
    logger.warning("雷达绑定验证令牌不存在 user_id=%s", user.id)
    return None


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
