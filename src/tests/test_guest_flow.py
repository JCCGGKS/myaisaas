"""游客模式集成测试：用 TestClient 走通完整闭环。

覆盖：游客识别（cookie）→ 建雷达（限 1）→ 绑渠道（限 1）→ 超限 limit_exceeded
→ 注册解锁 → 限额解除。
"""
from fastapi.testclient import TestClient


def test_guest_identified_and_empty(client: TestClient):
    # 首次请求无 cookie → 后端识别游客并写回 wa_uid
    r = client.get("/api/radars")
    assert r.status_code == 200
    assert r.json() == []
    assert "wa_uid" in client.cookies


def test_guest_radar_limit(client: TestClient):
    # 第一个雷达可建
    r = client.post("/api/radars", json={"raw_query": "LISA 演唱会动态"})
    assert r.status_code == 201
    radar_id = r.json()["id"]
    assert r.json()["raw_query"] == "LISA 演唱会动态"

    # 列表可见，事件流为空
    r = client.get("/api/radars")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(f"/api/radars/{radar_id}/events")
    assert r.status_code == 200
    assert r.json() == []

    # 第二个雷达 → 触发游客限额 402
    r = client.post("/api/radars", json={"raw_query": "OpenAI 动态"})
    assert r.status_code == 402
    assert r.json()["code"] == "limit_exceeded"


def test_guest_channel_limit(client: TestClient):
    # 渠道列表：telegram / email / webhook 三类，初始均未绑定
    r = client.get("/api/channels")
    assert r.status_code == 200
    bodies = {c["type"]: c for c in r.json()}
    assert set(bodies) == {"telegram", "email", "webhook"}
    assert all(not c["bound"] for c in bodies.values())

    # 绑定 telegram → 返回 connect_url
    r = client.post("/api/channels/telegram/bind")
    assert r.status_code == 200
    body = r.json()
    assert body["bound"] is True
    assert "connect_url" in body

    # 绑定第二个不同渠道 email → 触发游客限额 402
    r = client.post("/api/channels/email/bind", json={"recipient": "me@example.com"})
    assert r.status_code == 402
    assert r.json()["code"] == "limit_exceeded"


def test_register_lifts_guest_limit(client: TestClient):
    # 先占满游客限额：1 雷达 + 1 渠道
    client.post("/api/radars", json={"raw_query": "雷达 A"})
    client.post("/api/channels/telegram/bind")

    # 超限确认
    assert client.post("/api/radars", json={"raw_query": "雷达 B"}).status_code == 402

    # 注册 → 升级为真实账号，解除限额
    r = client.post("/api/auth/register", json={"email": "user@example.com", "password": "pw123"})
    assert r.status_code == 200
    assert r.json()["is_guest"] is False
    assert "wa_uid" in client.cookies  # 写入 token cookie

    # 限额解除：可继续建雷达、绑更多渠道
    r = client.post("/api/radars", json={"raw_query": "雷达 B"})
    assert r.status_code == 201

    r = client.post("/api/channels/email/bind", json={"recipient": "me@example.com"})
    assert r.status_code == 200
    assert r.json()["bound"] is True


def test_login_unknown_account_rejected(client: TestClient):
    r = client.post("/api/auth/login", json={"email": "nope@example.com", "password": "x"})
    assert r.status_code == 404
    assert r.json()["code"] is None or "code" in r.json()


def test_create_radar_empty_query_rejected(client: TestClient):
    r = client.post("/api/radars", json={"raw_query": "   "})
    assert r.status_code in (400, 422)


def test_bind_backfills_radar_channel(client: TestClient):
    # 先建雷达（未绑渠道，notify_channel 为空）
    client.post("/api/radars", json={"raw_query": "雷达 A"})
    # 绑定 telegram 后，雷达的 notify_channel 应回填为该渠道
    r = client.post("/api/channels/telegram/bind")
    assert r.status_code == 200
    radars = client.get("/api/radars").json()
    assert radars[0]["notify_channel"] == "telegram"
