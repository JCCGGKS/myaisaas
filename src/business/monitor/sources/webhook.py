"""Webhook 数据源：不主动抓取，由 /api/ingest 把外部推送转成 RawItem。"""
from .base import RawItem


class WebhookSource:
    @staticmethod
    def from_payload(source_type: str, payload) -> list[RawItem]:
        if isinstance(payload, list):
            return [WebhookSource._one(source_type, p) for p in payload]
        return [WebhookSource._one(source_type, payload)]

    @staticmethod
    def _one(source_type: str, p: dict) -> RawItem:
        p = p or {}
        return RawItem(
            title=p.get("title", ""),
            url=p.get("url"),
            content=p.get("content", ""),
            source_id=f"webhook:{source_type}",
        )
