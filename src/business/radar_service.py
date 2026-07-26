"""雷达业务：创建（含 LLM 解析 + 游客限额）/ 列表 / 详情 / 暂停恢复。

创建时调用 pkgs.llm.parser 把自然语言解析为结构化参数；
LLM 不可用时自动降级（不阻断创建）。
"""
from datetime import datetime, timezone

from data.engine import Session
from dao.radar_dao import count_by_owner, create, delete as delete_radar_dao, get, list_by_owner, set_channels, update_scan_state
from config.settings import settings
from model.user import User
from pkgs.llm.parser import parse_query
from business.monitor.sources import default_news_source, is_fetchable
from utils.exceptions import AppError, LimitExceededError
from utils.logging import get_logger

logger = get_logger(__name__)


async def create_radar(db: Session, user: User, raw_query: str, notify_channels: list[str] | None = None) -> object:
    raw_query = (raw_query or "").strip()
    if not raw_query:
        raise AppError("监控目标不能为空", status_code=422, code="invalid_input")

    if user.is_guest and count_by_owner(db, user.id) >= settings.guest_radar_limit:
        raise LimitExceededError("游客最多创建 1 个雷达，登录解锁更多")

    # LLM 解析自然语言 → 结构化参数（llm=None 时降级）
    parsed = await parse_query(raw_query, llm=None)
    sources = parsed.get("sources") or []
    # 没有任何可抓取的源（如降级得到的 web+query）时，补一个真实 RSS 源（Google News 搜索），
    # 保证监控循环能真正拉到相关条目，而不是空转。
    if not any(is_fetchable(s) for s in sources):
        sources = [default_news_source(raw_query)]
        logger.info("雷达无可用源，使用默认真实源: %s", sources[0]["url"])
    radar = create(
        db,
        user.id,
        raw_query,
        notify_channels=notify_channels,
        keywords=parsed.get("keywords"),
        sources=sources,
        filters=parsed.get("filters"),
    )
    logger.info("雷达创建成功 user_id=%s radar_id=%s channels=%s", user.id, radar.id, radar.notify_channels)
    return radar


def list_radars(db: Session, user: User):
    return list_by_owner(db, user.id)


def get_radar(db: Session, user: User, radar_id: int):
    radar = get(db, radar_id)
    if radar is None or radar.owner_id != user.id or radar.deleted_at is not None:
        raise AppError("雷达不存在", status_code=404, code="not_found")
    return radar


def set_radar_channels(db: Session, user: User, radar_id: int, channels: list[str]) -> object:
    radar = get_radar(db, user, radar_id)
    return set_channels(db, radar_id, channels)


def pause_radar(db: Session, user: User, radar_id: int) -> object:
    radar = get_radar(db, user, radar_id)
    update_scan_state(db, radar, dict(radar.scan_state or {}), status="paused")
    logger.info("雷达暂停 radar_id=%s", radar_id)
    return radar


def resume_radar(db: Session, user: User, radar_id: int) -> object:
    radar = get_radar(db, user, radar_id)
    update_scan_state(db, radar, dict(radar.scan_state or {}), status="active", last_error=None)
    logger.info("雷达恢复 radar_id=%s", radar_id)
    return radar


def delete_radar(db: Session, user: User, radar_id: int) -> object:
    # get_radar 已做归属 + active 校验（非本人/已删均 404），天然防越权删除
    radar = get_radar(db, user, radar_id)
    delete_radar_dao(db, radar.id)
    logger.info("雷达删除 radar_id=%s owner=%s", radar.id, user.id)
    return radar
