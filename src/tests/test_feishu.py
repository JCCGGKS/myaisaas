"""Feishu 渠道测试：

- FeishuChannel：payload 构造（含签名）、空 url、发送成功/失败路径；
  外部 HTTP 通过替换实例方法 _post 隔离，不依赖真实飞书服务。
- 绑定流程：经 API 绑定飞书 webhook 直接 verified；非法 webhook 返回 422。
"""
import asyncio

from business.notifier.channels import FeishuChannel, PushMessage
from business.channel_service import _is_feishu_webhook


def test_is_feishu_webhook():
    assert _is_feishu_webhook("https://open.feishu.cn/open-apis/bot/v2/hook/abc")
    assert _is_feishu_webhook("https://open.larksuite.com/open-apis/bot/v2/hook/abc")
    assert not _is_feishu_webhook("http://open.feishu.cn/open-apis/bot/v2/hook/abc")
    assert not _is_feishu_webhook("https://example.com/hook/abc")
    assert not _is_feishu_webhook("")


def test_build_payload_without_sign():
    ch = FeishuChannel()
    p = ch._build_payload(PushMessage(title="标题", body="正文", url="http://x"))
    assert p["msg_type"] == "interactive"
    assert "timestamp" not in p and "sign" not in p
    assert p["card"]["header"]["title"]["content"] == "标题"
    assert p["card"]["elements"][1]["actions"][0]["url"] == "http://x"


def test_build_payload_with_sign():
    ch = FeishuChannel(sign_secret="s3cret")
    p = ch._build_payload(PushMessage(title="t", body="b"))
    assert "timestamp" in p and "sign" in p
    # sign 必须与本地算法一致（飞书服务端据此校验）
    assert p["sign"] == FeishuChannel._gen_sign("s3cret", p["timestamp"])


def test_send_empty_url_returns_false():
    ch = FeishuChannel()
    called = []
    ch._post = lambda url, payload: called.append((url, payload))
    ok = asyncio.run(ch.send("", PushMessage(title="t", body="b")))
    assert ok is False
    assert called == []  # 空 url 不应发起请求


def test_send_success():
    ch = FeishuChannel()
    recorded = []
    ch._post = lambda url, payload: recorded.append((url, payload))
    ok = asyncio.run(ch.send("https://open.feishu.cn/open-apis/bot/v2/hook/x",
                             PushMessage(title="命中", body="有更新")))
    assert ok is True
    assert len(recorded) == 1
    assert recorded[0][0].endswith("/hook/x")
    assert recorded[0][1]["msg_type"] == "interactive"


def test_send_failure_returns_false():
    ch = FeishuChannel()
    def _boom(url, payload):
        raise RuntimeError("network down")
    ch._post = _boom
    ok = asyncio.run(ch.send("https://open.feishu.cn/open-apis/bot/v2/hook/x",
                             PushMessage(title="t", body="b")))
    assert ok is False


def test_bind_feishu_via_api(client):
    # 绑定跟随雷达：先建雷达，再绑定到该雷达（POST 返回 dict，FastAPI 合并 guest cookie）
    r0 = client.post("/api/radars", json={"raw_query": "飞书测试雷达"})
    assert r0.status_code == 201
    radar_id = r0.json()["id"]

    r = client.post("/api/channels/feishu/bind",
                    json={"recipient": "https://open.feishu.cn/open-apis/bot/v2/hook/abc123",
                          "radar_id": radar_id})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "feishu" and body["bound"] and body["verified"]

    # 渠道列表应反映该雷达 feishu 已绑定（验证 cookie 已写回、跨请求一致）
    lst = client.get("/api/channels", params={"radar_id": radar_id}).json()
    feishu = next(c for c in lst if c["type"] == "feishu")
    assert feishu["bound"] and feishu["verified"]


def test_bind_feishu_invalid_webhook(client):
    r0 = client.post("/api/radars", json={"raw_query": "飞书测试雷达2"})
    assert r0.status_code == 201
    radar_id = r0.json()["id"]
    r = client.post("/api/channels/feishu/bind",
                    json={"recipient": "https://example.com/foo", "radar_id": radar_id})
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_input"
