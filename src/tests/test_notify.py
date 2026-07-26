"""多通道通知分发集成测试：注册用户绑两个渠道，扫描命中后两渠道均推送且防重发。"""
import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from business.monitor.scanner import scan_radar
from business.monitor.sources.base import RawItem, Source
from dao.radar_dao import get as get_radar
from dao.user_dao import get_by_email, get_by_id
from data.engine import SessionLocal
from model.event import Event
from model.notification import Notification


class FakeSource(Source):
    source_type = "fake"

    def __init__(self, items):
        self._items = items

    def source_id(self):
        return "fake:1"

    async def fetch(self, state=None):
        return self._items


def test_notify_multi_channel(client: TestClient):
    # 先占游客限额，再注册解锁
    client.post("/api/radars", json={"raw_query": "LISA 演唱会"})
    client.post("/api/auth/register", json={"email": "u@e.com", "password": "pw"})

    db0 = SessionLocal()
    user = get_by_email(db0, "u@e.com")
    db0.close()

    # 绑定 telegram（回填 chat_id）与 email
    client.post("/api/channels/telegram/bind")
    client.post("/webhooks/telegram", json={"user_id": user.id, "chat_id": "chat-1"})
    client.post("/api/channels/email/bind", json={"recipient": "me@e.com"})

    # 创建雷达并指定多通道
    r = client.post(
        "/api/radars",
        json={"raw_query": "LISA 演唱会", "notify_channels": ["telegram", "email"]},
    )
    rid = r.json()["id"]

    db = SessionLocal()
    radar = get_radar(db, rid)
    user = get_by_id(db, radar.owner_id)
    items = [RawItem("LISA 演唱会官宣", "u1", "", "fake:1")]
    asyncio.run(scan_radar(db, radar, user, llm=None, sources=[FakeSource(items)]))

    evs = db.scalars(select(Event).where(Event.radar_id == rid)).all()
    assert len(evs) == 1
    assert set(evs[0].pushed_channels) == {"telegram", "email"}

    nots = db.scalars(select(Notification).where(Notification.event_id == evs[0].id)).all()
    assert {n.channel for n in nots} == {"telegram", "email"}
    db.close()
