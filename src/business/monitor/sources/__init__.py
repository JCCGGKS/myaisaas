"""数据源连接器注册与工厂。"""
from urllib.parse import quote

from .base import RawItem, Source, make_dedup_key
from .rss import RSSSource
from .web import WebSource
from .webhook import WebhookSource

_REGISTRY = {"rss": RSSSource, "web": WebSource}


def default_news_source(query: str) -> dict:
    """默认真实源：Google News 按关键词的 RSS 搜索（无需 API key）。

    雷达没有任何可抓取源时的兜底，保证监控循环能真正拉到与监控目标相关的条目，
    而非卡在「web+query」（WebSource 无 url 时抓不到东西）。
    """
    q = quote((query or "").strip())
    return {
        "type": "rss",
        "url": f"https://news.google.com/rss/search?q={q}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    }


def is_fetchable(spec: dict) -> bool:
    """源是否真的可抓取：rss/web 且带 url。"""
    st = (spec.get("type") or "").lower()
    if st not in ("rss", "web"):
        return False
    return bool(spec.get("url"))


def build_source(spec: dict) -> Source:
    """由雷达的 sources 配置项构建对应 Source 实例。"""
    st = (spec.get("type") or "").lower()
    if st not in _REGISTRY:
        raise ValueError(f"unknown source type: {st}")
    if st == "rss":
        return RSSSource(url=spec.get("url"))
    if st == "web":
        return WebSource(url=spec.get("url"), query=spec.get("query"))
    raise ValueError(f"unsupported source type: {st}")


__all__ = [
    "RawItem",
    "Source",
    "make_dedup_key",
    "RSSSource",
    "WebSource",
    "WebhookSource",
    "build_source",
    "default_news_source",
    "is_fetchable",
]
