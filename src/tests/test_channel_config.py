"""渠道配置测试：CHANNEL_TYPES 从 etc/channels.json 加载（含回退），并驱动 list/bind。"""
import json
from pathlib import Path

import pytest

from business import channel_service as cs
from data.engine import SessionLocal
from model.user import User
from utils.exceptions import AppError


def _tmp_channels_json(tmp_path: Path, channels) -> Path:
    p = tmp_path / "channels.json"
    p.write_text(json.dumps({"channels": channels}, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_channel_types_from_json(tmp_path, monkeypatch):
    p = _tmp_channels_json(tmp_path, [
        {"type": "email"}, {"type": "sms"}, {"type": "webpush"},
    ])
    monkeypatch.setattr(cs, "_CHANNELS_JSON", p)
    assert cs._load_channel_types() == ["email", "sms", "webpush"]


def test_load_channel_types_empty_falls_back(tmp_path, monkeypatch):
    p = _tmp_channels_json(tmp_path, [])
    monkeypatch.setattr(cs, "_CHANNELS_JSON", p)
    assert cs._load_channel_types() == list(cs._FALLBACK_CHANNEL_TYPES)


def test_load_channel_types_missing_file_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "_CHANNELS_JSON", tmp_path / "nope.json")
    assert cs._load_channel_types() == list(cs._FALLBACK_CHANNEL_TYPES)


def test_list_channels_uses_configured_types(tmp_path, monkeypatch):
    # list_channels 遍历模块级 CHANNEL_TYPES；改配置即改返回
    monkeypatch.setattr(cs, "CHANNEL_TYPES", ["email", "sms"])
    db = SessionLocal()
    user = User(device_id="chan_test_1", is_guest=True, channel_bindings=[])
    db.add(user)
    db.commit()
    db.refresh(user)
    try:
        out = cs.list_channels(db, user)
        assert [c["type"] for c in out] == ["email", "sms"]
        assert all("bound" in c and "verified" in c for c in out)
    finally:
        db.delete(user)
        db.commit()
        db.close()


def test_bind_unknown_channel_rejected(tmp_path, monkeypatch):
    import asyncio

    monkeypatch.setattr(cs, "CHANNEL_TYPES", ["email"])
    db = SessionLocal()
    user = User(device_id="chan_test_2", is_guest=True, channel_bindings=[])
    db.add(user)
    db.commit()
    db.refresh(user)
    try:
        with pytest.raises(AppError) as exc:
            asyncio.run(cs.bind_channel(db, user, "telegram", ""))
        assert exc.value.code == "unknown_channel"
    finally:
        db.delete(user)
        db.commit()
        db.close()
