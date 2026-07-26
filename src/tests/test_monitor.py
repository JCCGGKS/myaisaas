"""监控扫描集成测试：FakeSource + 降级打分，验证 阈值过滤 / 去重 / 落库 / ingest。"""
import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from business.monitor.scanner import scan_radar
from business.monitor.sources.base import RawItem, Source
from dao.radar_dao import get as get_radar
from dao.user_dao import get_by_id
from data.engine import SessionLocal
from model.event import Event


class FakeSource(Source):
    source_type = "fake"

    def __init__(self, items):
        self._items = items

    def source_id(self):
        return "fake:1"

    async def fetch(self, state=None):
        return self._items


def _items():
    return [
        RawItem("LISA 演唱会官宣", "u1", "", "fake:1"),  # 命中关键词
        RawItem("无关财经新闻", "u2", "", "fake:1"),       # 不命中 → 低于阈值丢弃
    ]


def test_scan_threshold_and_dedup(client: TestClient):
    r = client.post("/api/radars", json={"raw_query": "LISA 演唱会"})
    rid = r.json()["id"]

    db = SessionLocal()
    radar = get_radar(db, rid)
    user = get_by_id(db, radar.owner_id)

    # 第一轮扫描：仅 LISA 命中阈值，落 1 条
    pushed = asyncio.run(scan_radar(db, radar, user, llm=None, sources=[FakeSource(_items())]))
    evs = db.scalars(select(Event).where(Event.radar_id == rid)).all()
    assert len(evs) == 1
    assert evs[0].title == "LISA 演唱会官宣"
    assert evs[0].relevance_score == 1.0

    # 第二轮扫描：相同条目应去重，仍 1 条
    asyncio.run(scan_radar(db, radar, user, llm=None, sources=[FakeSource(_items())]))
    evs2 = db.scalars(select(Event).where(Event.radar_id == rid)).all()
    assert len(evs2) == 1
    db.close()


def test_ingest_creates_event(client: TestClient):
    r = client.post("/api/radars", json={"raw_query": "LISA 演唱会"})
    rid = r.json()["id"]
    resp = client.post(
        "/api/ingest/webhook",
        json={"radar_id": rid, "items": [{"title": "LISA 演唱会最新消息", "url": "http://e", "content": ""}]},
    )
    assert resp.status_code == 200
    assert resp.json()["processed"] == 1

    db = SessionLocal()
    evs = db.scalars(select(Event).where(Event.radar_id == rid)).all()
    assert len(evs) == 1
    assert "LISA" in evs[0].title
    db.close()
