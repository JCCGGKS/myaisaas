"""RSS / Atom 数据源：抓取并解析条目。"""
import re
import xml.etree.ElementTree as ET

import httpx

from config.settings import settings
from utils.logging import get_logger
from .base import RawItem, Source

logger = get_logger(__name__)

_NS_ATOM = "{http://www.w3.org/2005/Atom}"


class RSSSource(Source):
    source_type = "rss"

    def __init__(self, url: str):
        self.url = url

    def source_id(self) -> str:
        return f"rss:{self.url}"

    async def fetch(self, state: dict | None = None) -> list[RawItem]:
        try:
            async with httpx.AsyncClient(
                timeout=settings.source.fetch_timeout,
                headers={"User-Agent": settings.source.user_agent},
                follow_redirects=True,
            ) as client:
                resp = await client.get(self.url)
                resp.raise_for_status()
                text = resp.text
        except Exception as exc:
            logger.error("RSS 抓取失败 %s: %s", self.url, exc)
            return []
        return self._parse(text)

    def _parse(self, text: str) -> list[RawItem]:
        items: list[RawItem] = []
        try:
            root = ET.fromstring(text)
        except Exception as exc:
            logger.error("RSS 解析失败: %s", exc)
            return []

        def _text(el, tag):
            node = el.find(tag)
            return (node.text or "").strip() if node is not None else ""

        for el in list(root.iter("item")) + list(root.iter(f"{_NS_ATOM}entry")):
            title = _text(el, "title") or _text(el, f"{_NS_ATOM}title")
            if not title:
                continue
            link = _text(el, "link") or _text(el, f"{_NS_ATOM}link")
            if not link:
                link_el = el.find(f"{_NS_ATOM}link")
                link = link_el.get("href") if link_el is not None else ""
            desc = _text(el, "description") or _text(el, "summary") or _text(el, f"{_NS_ATOM}summary")
            # 去掉 HTML 标签，留纯文本
            content = re.sub(r"<[^>]+>", " ", desc)
            items.append(RawItem(title=title, url=link or None, content=content[:500], source_id=self.source_id()))

        return items[: settings.monitor.max_items_per_source]
