"""轻量 asyncio 调度器：周期扫描 active 雷达（v1）。

- 生产可替换为 Celery+Redis；此处保持单进程零额外依赖，扫描/打分/分发逻辑不变。
- start() 在 FastAPI lifespan 中调用；trigger_scan() 供手动/ingest 即时触发。
"""
import asyncio

from config.settings import settings
from data.engine import SessionLocal
from utils.logging import get_logger
from .scanner import scan_all, scan_radar_by_id

logger = get_logger(__name__)


class MonitorScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                db = SessionLocal()
                n = await scan_all(db, llm=None)
                if n:
                    logger.info("调度扫描完成 radars=%d", n)
            except Exception as exc:  # 单次异常不应终止循环
                logger.error("扫描循环异常: %s", exc)
            finally:
                db.close()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=settings.monitor.scan_interval_seconds)
            except asyncio.TimeoutError:
                pass

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop())
        logger.info("监控调度启动 interval=%ss", settings.monitor.scan_interval_seconds)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await self._task
            except Exception:
                pass
            self._task = None

    async def trigger_scan(self, radar_id: int) -> bool:
        db = SessionLocal()
        try:
            return await scan_radar_by_id(db, radar_id, llm=None)
        finally:
            db.close()


# 全局单例（lifespan 启动/关闭）
scheduler = MonitorScheduler()
