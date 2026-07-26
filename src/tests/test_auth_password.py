"""鉴权密码集成测试：注册/登录走 bcrypt 哈希，错误密码被拒，存储非明文。"""
from fastapi.testclient import TestClient

from data.engine import SessionLocal
from dao.user_dao import get_by_email
from main import app


def _register(client: TestClient, email: str, password: str) -> int:
    # 先建一个雷达占住游客身份，再注册升级为账号
    client.post("/api/radars", json={"raw_query": "雷达 X"})
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()["user_id"]


def test_register_stores_hashed_password(client: TestClient):
    _register(client, "hash@wa.local", "secret123")
    with SessionLocal() as db:
        u = get_by_email(db, "hash@wa.local")
        assert u is not None
        assert u.password != "secret123"          # 不存明文
        assert u.password.startswith("$2")        # bcrypt 哈希


def test_login_correct_password(client: TestClient):
    _register(client, "login@wa.local", "secret123")
    # 新会话（新游客）用同一邮箱密码登录
    r = client.post("/api/auth/login", json={"email": "login@wa.local", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["is_guest"] is False
    assert r.json()["token"].startswith("eyJ")


def test_login_wrong_password_rejected(client: TestClient):
    _register(client, "wrong@wa.local", "secret123")
    # 用全新游客会话登录（带错密码）→ 应 401
    fresh = TestClient(app)
    r = fresh.post("/api/auth/login", json={"email": "wrong@wa.local", "password": "nope"})
    assert r.status_code == 401
    assert "密码" in r.json()["message"]


def test_register_existing_email_wrong_password_rejected(client: TestClient):
    _register(client, "dup@wa.local", "secret123")
    # 另一游客用同一邮箱但密码不符 → 拒绝（防冒用）
    fresh = TestClient(app)
    r = fresh.post("/api/auth/register", json={"email": "dup@wa.local", "password": "other"})
    assert r.status_code == 409


def test_logged_in_resubmit_does_not_overwrite_password(client: TestClient):
    # 注册后同一会话（cookie 即该账号）再次登录，即便密码不同也不应覆盖原密码
    _register(client, "resub@wa.local", "secret123")
    # 同会话、用错误密码再次登录：应仍成功（cookie 已认证），但密码不变
    r = client.post("/api/auth/login", json={"email": "resub@wa.local", "password": "typo"})
    assert r.status_code == 200
    # 用原始密码仍能在新会话登录 → 证明原密码未被覆盖
    fresh = TestClient(app)
    r2 = fresh.post("/api/auth/login", json={"email": "resub@wa.local", "password": "secret123"})
    assert r2.status_code == 200
