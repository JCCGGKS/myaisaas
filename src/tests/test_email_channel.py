"""EmailChannel 单元测试：MIME 构建与发送（mock smtplib，不真连网络）。"""
import asyncio
import smtplib
from unittest.mock import MagicMock

from business.notifier.channels import EmailChannel, PushMessage


def _patch_smtp(monkeypatch, raises=False):
    captured = {}

    def fake_init(self, host, port, timeout=10):
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr(smtplib.SMTP, "__init__", fake_init)
    if raises:
        monkeypatch.setattr(smtplib.SMTP, "send_message",
                            lambda self, message: (_ for _ in ()).throw(smtplib.SMTPException("boom")))
    else:
        monkeypatch.setattr(smtplib.SMTP, "send_message", lambda self, message: None)
    monkeypatch.setattr(smtplib.SMTP, "__enter__", lambda self: self)
    monkeypatch.setattr(smtplib.SMTP, "__exit__", lambda self, *a: None)
    return captured


def test_build_message_contains_subject_and_html():
    ch = EmailChannel(from_email="noreply@wa.local")
    msg = PushMessage(title="T", body="B", url="http://x")
    m = ch._build_message("a@b.com", msg)
    assert m["Subject"] == "T"
    assert m["To"] == "a@b.com"
    types = [p.get_content_type() for p in m.get_payload()]
    assert "text/plain" in types
    assert "text/html" in types


def test_send_via_smtp_called(monkeypatch):
    captured = _patch_smtp(monkeypatch)
    ch = EmailChannel(smtp_host="localhost", smtp_port=1025, from_email="n@wa.local")
    ok = asyncio.run(ch.send("a@b.com", PushMessage(title="T", body="B", url="http://x")))
    assert ok is True
    assert captured["host"] == "localhost"
    assert captured["port"] == 1025


def test_send_empty_recipient_false():
    ch = EmailChannel(smtp_host="localhost")
    ok = asyncio.run(ch.send("", PushMessage(title="T", body="B")))
    assert ok is False


def test_send_no_host_mock_true():
    # 未配置 host → 退回 mock（True），不连网络
    ch = EmailChannel(smtp_host="")
    ok = asyncio.run(ch.send("a@b.com", PushMessage(title="T", body="B")))
    assert ok is True


def test_send_smtp_error_returns_false(monkeypatch):
    _patch_smtp(monkeypatch, raises=True)
    ch = EmailChannel(smtp_host="localhost")
    ok = asyncio.run(ch.send("a@b.com", PushMessage(title="T", body="B")))
    assert ok is False
