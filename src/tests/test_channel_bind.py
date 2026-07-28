"""email 渠道绑定 + 验证测试（绑定跟随雷达）。

绑定写入「雷达」的 notify_channels，验证令牌也存于该雷达绑定；
QQ 号归一化。验证后仅该雷达的渠道生效，不污染其它雷达。
"""
from fastapi.testclient import TestClient

from data.engine import SessionLocal
from model.radar import Radar
from model.user import User


def _current_user_id(client: TestClient) -> int:
    return client.get("/api/auth/me").json()["user_id"]


def _create_radar(client: TestClient, raw_query: str) -> int:
    r = client.post("/api/radars", json={"raw_query": raw_query})
    assert r.status_code == 201
    return r.json()["id"]


def _email_binding(db, radar_id: int) -> dict:
    radar = db.get(Radar, radar_id)
    return next(b for b in radar.notify_channels if b["channel_type"] == "email")


def test_email_bind_then_verify(client: TestClient):
    client.post("/api/auth/register", json={"email": "cb@example.com", "password": "pw"})
    uid = _current_user_id(client)
    radar_id = _create_radar(client, "测试雷达")

    r = client.post(
        "/api/channels/email/bind",
        json={"recipient": "cb@example.com", "radar_id": radar_id},
    )
    assert r.status_code == 200
    assert r.json()["verified"] is False

    db = SessionLocal()
    try:
        binding = _email_binding(db, radar_id)
        token = binding["bind_token"]
        assert token
        assert binding["verified"] is False
    finally:
        db.close()

    # 凭令牌验证
    r2 = client.get("/api/channels/verify", params={"token": token})
    assert r2.status_code == 200
    assert r2.json()["ok"] is True

    # 验证后「该雷达」渠道生效
    r3 = client.get("/api/channels", params={"radar_id": radar_id})
    ch = {c["type"]: c for c in r3.json()}
    assert ch["email"]["verified"] is True
    assert ch["email"]["bound"] is True

    # 其它雷达不受影响（绑定跟随雷达，互不继承）
    other_radar = _create_radar(client, "另一个雷达")
    r4 = client.get("/api/channels", params={"radar_id": other_radar})
    ch4 = {c["type"]: c for c in r4.json()}
    assert ch4["email"]["bound"] is False


def test_email_bind_qq_normalization(client: TestClient):
    client.post("/api/auth/register", json={"email": "cb2@example.com", "password": "pw"})
    radar_id = _create_radar(client, "测试雷达2")

    r = client.post(
        "/api/channels/email/bind",
        json={"recipient": "123456", "radar_id": radar_id},
    )
    assert r.status_code == 200
    db = SessionLocal()
    try:
        assert _email_binding(db, radar_id)["recipient"] == "123456@qq.com"
    finally:
        db.close()


def test_verify_wrong_token_false(client: TestClient):
    client.post("/api/auth/register", json={"email": "cb3@example.com", "password": "pw"})
    radar_id = _create_radar(client, "测试雷达3")
    client.post(
        "/api/channels/email/bind",
        json={"recipient": "cb3@example.com", "radar_id": radar_id},
    )

    r = client.get("/api/channels/verify", params={"token": "nope"})
    assert r.status_code == 200
    assert r.json()["ok"] is False
