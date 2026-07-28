"""Web Push 渠道接入 e2e：绑定、校验、公钥下发、游客限额。"""
import json

from fastapi.testclient import TestClient


def _create_radar(client: TestClient, raw_query: str = "webpush 测试雷达") -> int:
    r = client.post("/api/radars", json={"raw_query": raw_query})
    assert r.status_code == 201
    return r.json()["id"]


VALID_SUB = {
    "endpoint": "https://push.example.com/sub/abc",
    "keys": {"p256dh": "BInvalidButShapeOk", "auth": "authsecret"},
}
INVALID_SUB = {"endpoint": "https://push.example.com/sub/abc"}  # 缺 keys


def test_vapid_public_key_endpoint(client: TestClient):
    # 测试环境未配置 VAPID 公钥，应返回空串（不报错）
    r = client.get("/api/channels/vapid-public-key")
    assert r.status_code == 200
    assert "vapid_public_key" in r.json()
    assert isinstance(r.json()["vapid_public_key"], str)


def test_webpush_bind_success(client: TestClient):
    client.post("/api/auth/register", json={"email": "wp@example.com", "password": "pw"})
    radar_id = _create_radar(client)

    r = client.post(
        "/api/channels/webpush/bind",
        json={"recipient": json.dumps(VALID_SUB), "radar_id": radar_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "webpush"
    assert body["bound"] is True
    assert body["verified"] is True  # 订阅即所有权证明，立即 verified

    # 列出来确认该雷达已绑 webpush 且 verified
    r2 = client.get("/api/channels", params={"radar_id": radar_id})
    ch = {c["type"]: c for c in r2.json()}
    assert ch["webpush"]["bound"] is True
    assert ch["webpush"]["verified"] is True


def test_webpush_bind_invalid_subscription(client: TestClient):
    client.post("/api/auth/register", json={"email": "wp2@example.com", "password": "pw"})
    radar_id = _create_radar(client)

    # 缺 keys -> 422
    r = client.post(
        "/api/channels/webpush/bind",
        json={"recipient": json.dumps(INVALID_SUB), "radar_id": radar_id},
    )
    assert r.status_code == 422

    # 非 JSON -> 422
    r2 = client.post(
        "/api/channels/webpush/bind",
        json={"recipient": "not-json", "radar_id": radar_id},
    )
    assert r2.status_code == 422


def test_guest_webpush_quota(client: TestClient):
    # 游客（不注册）：每个雷达最多 1 个渠道
    radar_id = _create_radar(client)

    r = client.post(
        "/api/channels/webpush/bind",
        json={"recipient": json.dumps(VALID_SUB), "radar_id": radar_id},
    )
    assert r.status_code == 200

    # 再绑 feishu 应触发游客限额（402 limit_exceeded）
    r2 = client.post(
        "/api/channels/feishu/bind",
        json={"recipient": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx", "radar_id": radar_id},
    )
    assert r2.status_code == 402
    assert r2.json().get("code") == "limit_exceeded"
