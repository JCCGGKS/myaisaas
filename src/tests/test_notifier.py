"""通知子系统测试：策略 + 工厂 + 分发（注入 FakeChannel，不真发消息）。"""
import asyncio

from business.notifier.channels import FakeChannel, PushMessage
from business.notifier.factory import ChannelFactory
from business.notifier.dispatch import dispatch


def test_factory_create_known():
    ch = ChannelFactory.create("telegram")
    assert isinstance(ch, FakeChannel.__bases__[0]) or ch.__class__.__name__ == "TelegramChannel"


def test_factory_unknown_raises():
    try:
        ChannelFactory.create("signal")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_factory_register_and_create_custom():
    class DummyChannel(FakeChannel):
        pass

    ChannelFactory.register("dummy", DummyChannel)
    ch = ChannelFactory.create("dummy")
    assert isinstance(ch, DummyChannel)


def test_fake_channel_records():
    fake = FakeChannel()
    asyncio.run(fake.send("chat", PushMessage(title="t", body="b")))
    assert len(fake.sent) == 1
    assert fake.sent[0][0] == "chat"


def test_dispatch_telegram_mock_returns_true():
    # 未配置 token 时走 mock，应返回 True（不中断主流程）
    ok = asyncio.run(dispatch("telegram", "123", PushMessage(title="命中", body="详情")))
    assert ok is True


def test_dispatch_webhook_with_empty_recipient_false():
    ok = asyncio.run(dispatch("webhook", "", PushMessage(title="t", body="b")))
    assert ok is False
