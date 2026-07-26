"""数据源连接器注册与工厂。"""
from .base import RawItem, Source, make_dedup_key
from .rss import RSSSource
from .web import WebSource
from .webhook import WebhookSource

_REGISTRY = {"rss": RSSSource, "web": WebSource}


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
]
