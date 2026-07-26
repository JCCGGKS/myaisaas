"""扫描编排：拉源 → 打分 → 去重 → 落库 → 多通道分发。

- scan_radar：扫描单个雷达；`sources` 可注入（测试用 FakeSource）。
- scan_all：扫描全部 active 雷达（调度器调用）。
- scan_radar_by_id：按 id 扫描（手动/ingest 触发）。
所有外部依赖（Source / LLM）均支持注入，便于在无网络/无 API key 下跑通。
"""
from datetime import datetime, timezone

from config.settings import settings
from dao.event_dao import create as create_event
from dao.event_dao import exists_by_dedup_keys
from dao.radar_dao import get, get_active, update_scan_state
from dao.user_dao import get_by_id
from pkgs.llm.scorer import score
from business.notifier.notify import notify_radar
from utils.logging import get_logger
from .sources import build_source, make_dedup_key

logger = get_logger(__name__)


async def _process_items(db, radar, user, raw_items: list, llm=None) -> bool:
    """对一批 RawItem 做：去重 → LLM 打分 → 阈值过滤 → 落库 → 多通道分发。"""
    keys = [make_dedup_key(it.source_id, it.url, it.title) for it in raw_items]
    seen = exists_by_dedup_keys(db, radar.id, keys)

    pushed_any = False
    for it in raw_items:
        key = make_dedup_key(it.source_id, it.url, it.title)
        if key in seen:
            continue
        relevance, summary = await score(it, radar, llm)
        if relevance < settings.relevance_threshold:
            logger.debug("低于阈值 radar=%s score=%.2f 丢弃: %s", radar.id, relevance, it.title)
            continue
        event = create_event(db, radar.id, key, it.title, it.url, relevance, summary)
        await notify_radar(event, radar, user, db)
        pushed_any = True
    return pushed_any


async def scan_radar(db, radar, user, llm=None, sources: list | None = None) -> bool:
    """扫描单个雷达，返回是否有事件被推送。"""
    scan_state = dict(radar.scan_state or {})
    specs = sources if sources is not None else [build_source(s) for s in (radar.sources or [])]

    try:
        raw_items = []
        for src in specs:
            try:
                fetched = await src.fetch(scan_state.get(src.source_id()))
            except Exception as exc:
                logger.error("源抓取异常 radar=%s src=%s: %s", radar.id, src.source_id(), exc)
                fetched = []
            raw_items.extend(fetched[: settings.max_items_per_source])

        pushed_any = await _process_items(db, radar, user, raw_items, llm)

        for src in specs:
            scan_state[src.source_id()] = "scanned"
        update_scan_state(db, radar, scan_state, last_scan_at=datetime.now(timezone.utc), status="active")
        return pushed_any
    except Exception as exc:
        logger.error("扫描雷达失败 radar=%s: %s", radar.id, exc)
        update_scan_state(db, radar, scan_state, last_scan_at=datetime.now(timezone.utc), status="error", last_error=str(exc)[:500])
        return False


async def scan_items(db, radar, user, raw_items: list, llm=None) -> bool:
    """直接处理一批外部推送进来的 RawItem（webhook/ingest 用，不主动抓取）。"""
    try:
        pushed_any = await _process_items(db, radar, user, raw_items, llm)
        update_scan_state(
            db, radar, dict(radar.scan_state or {}),
            last_scan_at=datetime.now(timezone.utc), status="active",
        )
        return pushed_any
    except Exception as exc:
        logger.error("处理推送条目失败 radar=%s: %s", radar.id, exc)
        update_scan_state(db, radar, dict(radar.scan_state or {}), last_scan_at=datetime.now(timezone.utc), status="error", last_error=str(exc)[:500])
        return False


async def scan_radar_by_id(db, radar_id: int, llm=None) -> bool:
    radar = get(db, radar_id)
    if radar is None:
        logger.warning("扫描不存在的雷达 %s", radar_id)
        return False
    user = get_by_id(db, radar.owner_id)
    if user is None:
        logger.warning("雷达 %s 无所属用户", radar_id)
        return False
    return await scan_radar(db, radar, user, llm)


async def scan_all(db, llm=None) -> int:
    """扫描全部 active 雷达，返回扫描数量。"""
    radars = get_active(db)
    count = 0
    for radar in radars:
        user = get_by_id(db, radar.owner_id)
        if user is None:
            continue
        await scan_radar(db, radar, user, llm)
        count += 1
    return count
