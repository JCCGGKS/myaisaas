"""通知分发测试：多通道推送 + 去重（防重发）。

email 在测试中因 WA_SMTP_HOST="" 走 mock（发送返回 True）；
webpush 本期未实现，用 FakeChannel 模拟第二个渠道以验证多通道与去重逻辑。
"""
import asyncio
from sqlalchemy import select

from business.notifier.channels import FakeChannel
from business.notifier.factory import ChannelFactory
from business.notifier.notify import notify_radar
from data.engine import SessionLocal
from model.event import Event
from model.notification import Notification
from model.radar import Radar
from model.user import User


def test_notify_multi_channel_and_dedup():
    # webpush 本期未实现，用 FakeChannel 模拟第二个渠道以验证多通道 + 去重
    original = ChannelFactory._registry.get("webpush")
    ChannelFactory.register("webpush", FakeChannel)

    db = SessionLocal()
    try:
        user = User(
            email="notify_test@example.com",
            password="x",
            is_guest=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 接收人直接来自雷达的 notify_channels（list[dict]），不再依赖 user.channel_bindings
        radar = Radar(
            owner_id=user.id,
            raw_query="q",
            notify_channels=[
                {"channel_type": "email", "recipient": "me@example.com", "verified": True},
                {"channel_type": "webpush", "recipient": "sub-x", "verified": True},
            ],
            active=True,
        )
        db.add(radar)
        db.commit()
        db.refresh(radar)

        event = Event(radar_id=radar.id, dedup_key="k1", title="命中", summary="详情", source_url="http://x")
        db.add(event)
        db.commit()
        db.refresh(event)

        # 首次推送：两渠道都应成功并记录 Notification
        pushed = asyncio.run(notify_radar(event, radar, user, db))
        assert set(pushed) == {"email", "webpush"}

        nots = db.scalars(select(Notification).where(Notification.event_id == event.id)).all()
        assert {n.channel for n in nots} == {"email", "webpush"}

        # 再次推送同一事件 → 去重，不应再新增 Notification，返回空
        pushed2 = asyncio.run(notify_radar(event, radar, user, db))
        assert pushed2 == []

        nots2 = db.scalars(select(Notification).where(Notification.event_id == event.id)).all()
        assert len(nots2) == 2

        # 清理，避免污染共享测试库
        for n in nots2:
            db.delete(n)
        db.delete(event)
        db.delete(radar)
        db.delete(user)
        db.commit()
    finally:
        if original is None:
            ChannelFactory._registry.pop("webpush", None)
        else:
            ChannelFactory._registry["webpush"] = original
        db.close()
