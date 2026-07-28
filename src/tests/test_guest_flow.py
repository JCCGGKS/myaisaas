"""游客模式集成测试：用 TestClient 走通完整闭环。

覆盖：游客识别（cookie）→ 建雷达（限 1）→ 绑渠道（限 1）→ 超限 limit_exceeded
→ 注册解锁 → 限额解除。

渠道模型（2026-07-26 起）：email / webpush / feishu；email 绑定后需验证邮件，
验证前 verified=False。
"""
from fastapi.testclient import TestClient


def test_guest_identified_and_empty(client: TestClient):
    # 首次请求无 cookie → 后端识别游客并写回 wa_guest
    r = client.get("/api/radars")
    assert r.status_code == 200
    assert r.json() == []
    assert "wa_guest" in client.cookies


def test_guest_radar_limit(client: TestClient):
    # 第一个雷达可建
    r = client.post("/api/radars", json={"raw_query": "LISA 演唱会动态"})
    assert r.status_code == 201
    radar_id = r.json()["id"]
    assert r.json()["raw_query"] == "LISA 演唱会动态"

    # 列表可见，事件流为空
    r = client.get(f"/api/radars/{radar_id}/events")
    assert r.status_code == 200
    assert r.json() == []

    # 第二个雷达 → 触发游客限额 402
    r = client.post("/api/radars", json={"raw_query": "OpenAI 动态"})
    assert r.status_code == 402
    assert r.json()["code"] == "limit_exceeded"


def test_guest_channel_limit(client: TestClient):
    # 绑定跟随雷达：先建雷达（渠道限额按「单个雷达」计）
    r = client.post("/api/radars", json={"raw_query": "雷达 A"})
    assert r.status_code == 201
    radar_id = r.json()["id"]

    # 渠道列表：email / webpush / feishu 三类，该雷达初始均未绑定
    r = client.get("/api/channels", params={"radar_id": radar_id})
    assert r.status_code == 200
    bodies = {c["type"]: c for c in r.json()}
    assert set(bodies) == {"email", "webpush", "feishu"}
    assert all(not c["bound"] for c in bodies.values())

    # 绑定 email → 返回 bound=True、verified=False（待验证邮件）
    r = client.post(
        "/api/channels/email/bind",
        json={"recipient": "me@example.com", "radar_id": radar_id},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bound"] is True
    assert body["verified"] is False

    # 同一雷达绑定第二个渠道 → 触发游客「每雷达」限额 402
    r = client.post(
        "/api/channels/feishu/bind",
        json={"recipient": "https://open.feishu.cn/open-apis/bot/v2/hook/abc", "radar_id": radar_id},
    )
    assert r.status_code == 402
    assert r.json()["code"] == "limit_exceeded"


def test_register_lifts_guest_limit(client: TestClient):
    # 先占满游客限额：1 雷达 + 在该雷达上绑 1 渠道
    client.post("/api/radars", json={"raw_query": "雷达 A"})
    radar_id = client.get("/api/radars").json()[0]["id"]
    client.post(
        "/api/channels/email/bind",
        json={"recipient": "me@example.com", "radar_id": radar_id},
    )

    # 超限确认（第二个雷达）
    assert client.post("/api/radars", json={"raw_query": "雷达 B"}).status_code == 402

    # 注册 → 升级为真实账号，解除限额
    r = client.post("/api/auth/register", json={"email": "user@example.com", "password": "pw123"})
    assert r.status_code == 200
    assert r.json()["is_guest"] is False
    assert "wa_auth" in client.cookies  # 写入 token cookie

    # 限额解除：可继续建雷达；在新雷达上重新绑 email 不再被限额拦截
    r = client.post("/api/radars", json={"raw_query": "雷达 B"})
    assert r.status_code == 201
    new_radar_id = r.json()["id"]

    r = client.post(
        "/api/channels/email/bind",
        json={"recipient": "me@example.com", "radar_id": new_radar_id},
    )
    assert r.status_code == 200
    assert r.json()["bound"] is True


def test_login_unknown_account_rejected(client: TestClient):
    r = client.post("/api/auth/login", json={"email": "nope@example.com", "password": "x"})
    assert r.status_code == 404
    assert r.json()["code"] is None or "code" in r.json()


def test_create_radar_empty_query_rejected(client: TestClient):
    r = client.post("/api/radars", json={"raw_query": "   "})
    assert r.status_code in (400, 422)


def test_bind_writes_to_radar_not_user(client: TestClient):
    # 新建雷达（未绑渠道，notify_channels 初始为空 list[dict]）
    client.post("/api/radars", json={"raw_query": "雷达 A"})
    radar_id = client.get("/api/radars").json()[0]["id"]
    # 绑定 email 后，雷达的 notify_channels 应含该渠道（list[dict]），而非用户级
    r = client.post(
        "/api/channels/email/bind",
        json={"recipient": "me@example.com", "radar_id": radar_id},
    )
    assert r.status_code == 200
    radars = client.get("/api/radars").json()
    nc = radars[0]["notify_channels"]
    assert any(isinstance(b, dict) and b.get("channel_type") == "email" for b in nc)
