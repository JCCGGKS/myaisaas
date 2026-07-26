"""数据源连接器注册与工厂。"""
from urllib.parse import quote

from .base import RawItem, Source, make_dedup_key
from .bing import BingWebSource
from .rss import RSSSource
from .web import WebSource
from .webhook import WebhookSource

_REGISTRY = {"rss": RSSSource, "web": WebSource, "bing": BingWebSource}


def default_news_source(query: str) -> dict:
    """默认真实源：Bing 网页搜索（按关键词），无需 API key。

    Google News RSS 在部分网络不可达、且 Bing 的 RSS 端点已失效（重定向到首页），
    故默认走 Bing 网页搜索 HTML 解析，保证监控循环能真正拉到与监控目标相关的条目，
    而非卡在「web+query」（WebSource 无 url 时抓不到东西）。
    """
    q = quote((query or "").strip())
    return {
        "type": "bing",
        "query": (query or "").strip(),
        "url": f"https://www.bing.com/search?q={q}&setlang=zh-CN",
    }


def is_fetchable(spec: dict) -> bool:
    """源是否真的可抓取：rss/web/bing 且带 url。"""
    st = (spec.get("type") or "").lower()
    if st not in ("rss", "web", "bing"):
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
    if st == "bing":
        return BingWebSource(url=spec.get("url"), query=spec.get("query"))
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
