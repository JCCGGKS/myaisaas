"""WebpushChannel 单元测试：用 monkeypatch 隔离 pywebpush.webpush，覆盖成功/失败/降级路径。"""
import json

import pytest

from business.notifier.channels import WebpushChannel, WebPushException, PushMessage
from business.notifier.factory import ChannelFactory

MSG = PushMessage(title="命中通知", body="有新的相关动态", url="http://localhost:8000/radars/1")


SUB = {
    "endpoint": "https://push.example.com/abc",
    "keys": {"p256dh": "BInvalidButShapeOk", "auth": "authsecret"},
}


class _FakeResp:
    def __init__(self, status_code):
        self.status_code = status_code


def test_factory_creates_webpush():
    ch = ChannelFactory.create("webpush")
    assert isinstance(ch, WebpushChannel)


def test_send_empty_subscription_returns_false():
    import asyncio

    ch = WebpushChannel(vapid_private_key="x", subject="mailto:t@t.io")

    async def run():
        return await ch.send("", MSG)

    assert asyncio.run(run()) is False  # recipient 为空


def test_send_invalid_json_returns_false():
    import asyncio

    ch = WebpushChannel(vapid_private_key="x", subject="mailto:t@t.io")

    async def run():
        return await ch.send("{not-json", MSG)

    assert asyncio.run(run()) is False


def test_send_missing_keys_returns_false():
    ch = WebpushChannel(vapid_private_key="x", subject="mailto:t@t.io")
    bad = json.dumps({"endpoint": "https://x", "keys": {"p256dh": "k"}})  # 缺 auth

    import asyncio

    async def run():
        return await ch.send(bad, MSG)

    assert asyncio.run(run()) is False


def test_send_no_vapid_key_mocks_success(monkeypatch):
    # 未配置私钥 -> 降级 mock 返回 True，且不真发
    captured = {}

    def fake_webpush(**kwargs):
        captured["called"] = True
        return None

    monkeypatch.setattr("business.notifier.channels.webpush", fake_webpush)
    ch = WebpushChannel(vapid_private_key="", subject="mailto:t@t.io")

    import asyncio

    async def run():
        return await ch.send(json.dumps(SUB), MSG)

    assert asyncio.run(run()) is True
    assert captured.get("called") is None  # 降级不应调用 webpush


def test_send_success_calls_webpush(monkeypatch):
    captured = {}

    def fake_webpush(**kwargs):
        captured["kwargs"] = kwargs
        return None

    monkeypatch.setattr("business.notifier.channels.webpush", fake_webpush)
    ch = WebpushChannel(vapid_private_key="priv", subject="mailto:t@t.io")

    import asyncio

    async def run():
        return await ch.send(json.dumps(SUB), MSG)

    assert asyncio.run(run()) is True
    assert captured["kwargs"]["vapid_private_key"] == "priv"
    assert captured["kwargs"]["vapid_claims"] == {"sub": "mailto:t@t.io"}


def test_send_gone_subscription_returns_false(monkeypatch):
    def fake_webpush(**kwargs):
        raise WebPushException("gone", response=_FakeResp(410))

    monkeypatch.setattr("business.notifier.channels.webpush", fake_webpush)
    ch = WebpushChannel(vapid_private_key="priv", subject="mailto:t@t.io")

    import asyncio

    async def run():
        return await ch.send(json.dumps(SUB), MSG)

    assert asyncio.run(run()) is False


def test_send_other_webpush_error_returns_false(monkeypatch):
    def fake_webpush(**kwargs):
        raise WebPushException("boom", response=_FakeResp(500))

    monkeypatch.setattr("business.notifier.channels.webpush", fake_webpush)
    ch = WebpushChannel(vapid_private_key="priv", subject="mailto:t@t.io")

    import asyncio

    async def run():
        return await ch.send(json.dumps(SUB), MSG)

    assert asyncio.run(run()) is False
