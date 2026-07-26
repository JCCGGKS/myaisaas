"""鉴权补充接口测试：/api/auth/me 与 /api/auth/logout。"""
from fastapi.testclient import TestClient


def test_me_as_guest(client: TestClient):
    # 无登录的游客：me 返回 is_guest=True 且无 email
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["is_guest"] is True
    assert body["email"] is None
    assert "channel_bindings" not in body


def test_me_after_register(client: TestClient):
    # 注册升级后：me 应反映真实账号（非游客 + email）
    r = client.post("/api/auth/register", json={"email": "me@example.com", "password": "pw123"})
    assert r.status_code == 200

    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["is_guest"] is False
    assert body["email"] == "me@example.com"


def test_me_user_id_matches_register(client: TestClient):
    reg = client.post("/api/auth/register", json={"email": "me2@example.com", "password": "pw123"})
    assert reg.status_code == 200
    reg_id = reg.json()["user_id"]

    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["user_id"] == reg_id


def test_logout_clears_cookie(client: TestClient):
    # 登录后持有 token cookie
    client.post("/api/auth/register", json={"email": "out@example.com", "password": "pw123"})
    assert "wa_auth" in client.cookies

    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # 登出后 cookie 被清除：再次 me 又变回游客（新游客）
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["is_guest"] is True


def test_register_persists_name(client: TestClient):
    # 注册时带昵称 → /me 应返回该昵称
    client.post("/api/auth/register", json={"email": "named@example.com", "password": "pw123", "name": "小雷达"})
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["is_guest"] is False
    assert body["name"] == "小雷达"
    assert body["email"] == "named@example.com"
