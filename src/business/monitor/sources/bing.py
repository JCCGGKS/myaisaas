"""Bing 网页搜索源：抓取 Bing 搜索结果页 HTML 并解析条目。

背景：Google News RSS 在部分网络不可达；Bing 的 RSS 端点也已失效（重定向到首页），
因此用 Bing **网页搜索**的 HTML 解析作为默认可达源，保证监控循环能真实拉到相关条目。
"""
import base64
import re
from html import unescape

import httpx

from config.settings import settings
from utils.logging import get_logger
from .base import RawItem, Source

logger = get_logger(__name__)


class BingWebSource(Source):
    source_type = "bing"

    def __init__(self, url: str, query: str | None = None):
        self.url = url
        self.query = query or ""

    def source_id(self) -> str:
        return f"bing:{self.query or self.url}"

    @staticmethod
    def _decode_redirect(href: str) -> str:
        """Bing 结果链接有时包成 bing.com/ck/a?...&u=a1<base64url> 跳转，解出真实 URL。"""
        m = re.search(r"[?&]u=a1([^&]+)", href)
        if not m:
            return href
        s = m.group(1)
        s += "=" * (-len(s) % 4)
        try:
            return base64.urlsafe_b64decode(s).decode("utf-8")
        except Exception:
            return href

    async def fetch(self, state: dict | None = None) -> list[RawItem]:
        try:
            async with httpx.AsyncClient(
                timeout=settings.source_fetch_timeout,
                headers={
                    "User-Agent": settings.source_user_agent,
                    "Accept-Language": "zh-CN,zh;q=0.9",
                },
                follow_redirects=True,
            ) as client:
                resp = await client.get(self.url)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.error("Bing 搜索抓取失败 %s: %s", self.url, exc)
            return []
        return self._parse(html)

    def _parse(self, html: str) -> list[RawItem]:
        items: list[RawItem] = []
        # 每个自然结果块 <li class="b_algo">…</li>；按边界切分，兼容最后一个块无尾随 </ol>
        for part in html.split('<li class="b_algo"')[1:]:
            m = re.search(r"</li>\s*(?=<li class=\"b_algo\"|</ol>|</ul>|$)", part)
            block = part[: m.start()] if m else part
            hm = re.search(r"<h2[^>]*>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", block, re.S)
            if not hm:
                continue
            href = self._decode_redirect(hm.group(1))
            title = unescape(re.sub(r"<[^>]+>", "", hm.group(2))).strip()
            if not title:
                continue
            # 摘要：优先 b_lineclamp，否则首个 <p>
            sm = re.search(r'<p[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>', block, re.S)
            if not sm:
                sm = re.search(r"<p[^>]*>(.*?)</p>", block, re.S)
            snippet = re.sub(r"<[^>]+>", " ", sm.group(1) if sm else "").strip() if sm else ""
            snippet = unescape(re.sub(r"\s+", " ", snippet))[:500]
            items.append(RawItem(title=title, url=href or None, content=snippet, source_id=self.source_id()))
        return items[: settings.max_items_per_source]
