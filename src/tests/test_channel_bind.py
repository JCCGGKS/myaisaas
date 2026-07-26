"""email 渠道绑定 + 验证测试：绑定后待验证，凭令牌验证后生效；QQ 号归一化。"""
from fastapi.testclient import TestClient

from data.engine import SessionLocal
from model.user import User


def _current_user_id(client: TestClient) -> int:
    return client.get("/api/auth/me").json()["user_id"]


def _email_binding(client: TestClient, user_id: int) -> dict:
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        return next(b for b in user.channel_bindings if b["channel_type"] == "email")
    finally:
        db.close()


def test_email_bind_then_verify(client: TestClient):
    client.post("/api/auth/register", json={"email": "cb@example.com", "password": "pw"})
    uid = _current_user_id(client)

    r = client.post("/api/channels/email/bind", json={"recipient": "cb@example.com"})
    assert r.status_code == 200
    assert r.json()["verified"] is False

    binding = _email_binding(client, uid)
    token = binding["bind_token"]
    assert token
    assert binding["verified"] is False

    # 凭令牌验证
    r2 = client.get("/api/channels/verify", params={"token": token})
    assert r2.status_code == 200
    assert r2.json()["ok"] is True

    # 验证后渠道生效
    r3 = client.get("/api/channels")
    ch = {c["type"]: c for c in r3.json()}
    assert ch["email"]["verified"] is True


def test_email_bind_qq_normalization(client: TestClient):
    client.post("/api/auth/register", json={"email": "cb2@example.com", "password": "pw"})
    uid = _current_user_id(client)

    r = client.post("/api/channels/email/bind", json={"recipient": "123456"})
    assert r.status_code == 200
    binding = _email_binding(client, uid)
    assert binding["recipient"] == "123456@qq.com"


def test_verify_wrong_token_false(client: TestClient):
    client.post("/api/auth/register", json={"email": "cb3@example.com", "password": "pw"})
    client.post("/api/channels/email/bind", json={"recipient": "cb3@example.com"})

    r = client.get("/api/channels/verify", params={"token": "nope"})
    assert r.status_code == 200
    assert r.json()["ok"] is False
