"""Web 数据源：抓取网页并抽取链接作为候选条目（MVP 简易解析）。"""
import re

import httpx

from config.settings import settings
from utils.logging import get_logger
from .base import RawItem, Source

logger = get_logger(__name__)

_LINK_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)


class WebSource(Source):
    source_type = "web"

    def __init__(self, url: str | None = None, query: str | None = None):
        self.url = url
        self.query = query

    def source_id(self) -> str:
        return f"web:{self.url or self.query or 'default'}"

    async def fetch(self, state: dict | None = None) -> list[RawItem]:
        target = self.url
        if not target:
            # MVP：没有通用搜索 API；仅当显式给了 url 才抓取，query 留作说明
            logger.debug("WebSource 无 url，跳过（query=%s）", self.query)
            return []
        try:
            async with httpx.AsyncClient(
                timeout=settings.source_fetch_timeout,
                headers={"User-Agent": settings.source_user_agent},
                follow_redirects=True,
            ) as client:
                resp = await client.get(target)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.error("Web 抓取失败 %s: %s", target, exc)
            return []
        return self._extract(html)

    def _extract(self, html: str) -> list[RawItem]:
        items: list[RawItem] = []
        for m in _LINK_RE.finditer(html):
            url = m.group(1)
            text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if not text:
                continue
            items.append(RawItem(title=text[:200], url=url, content=text, source_id=self.source_id()))
        return items[: settings.max_items_per_source]
