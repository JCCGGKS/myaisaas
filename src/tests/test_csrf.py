"""CSRF Origin 校验测试：开启后，合法 Origin 放行、伪造/缺失 Origin 拒绝 403。

其他用例因 conftest 设 WA_CSRF_ENABLED=false 跳过校验；本文件临时开启覆盖。
"""
import pytest
from fastapi.testclient import TestClient

from config.settings import settings
from main import app


@pytest.fixture
def csrf_client(monkeypatch):
    # 临时开启 CSRF 并设定受信前端源
    monkeypatch.setattr(settings, "csrf_enabled", True)
    monkeypatch.setattr(
        settings, "csrf_trusted_origins", ["http://localhost:5173"]
    )
    return TestClient(app)


def test_safe_method_no_origin_allowed(csrf_client: TestClient):
    # GET 不校验 Origin
    r = csrf_client.get("/api/channels")
    assert r.status_code == 200


def test_write_trusted_origin_allowed(csrf_client: TestClient):
    # 受信前端源发起的写请求放行
    r = csrf_client.post(
        "/api/channels/email/bind",
        json={"recipient": "x@example.com"},
        headers={"Origin": "http://localhost:5173"},
    )
    # 200（绑定成功）或 402/501 等下游业务码均可，关键不是 403
    assert r.status_code != 403


def test_write_forged_origin_rejected(csrf_client: TestClient):
    r = csrf_client.post(
        "/api/channels/email/bind",
        json={"recipient": "x@example.com"},
        headers={"Origin": "http://evil.example.com"},
    )
    assert r.status_code == 403


def test_write_missing_origin_rejected(csrf_client: TestClient):
    r = csrf_client.post(
        "/api/channels/email/bind",
        json={"recipient": "x@example.com"},
    )
    assert r.status_code == 403


def test_write_same_host_origin_allowed(csrf_client: TestClient):
    # Origin 与 Host 同源（本站）放行
    r = csrf_client.post(
        "/api/channels/email/bind",
        json={"recipient": "x@example.com"},
        headers={"Origin": "http://testserver", "Host": "testserver"},
    )
    assert r.status_code != 403
