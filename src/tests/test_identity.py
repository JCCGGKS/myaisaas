"""resolve_user 双 cookie 解析逻辑单元测试（docs/01_guest.md 方案）。"""
from data.engine import SessionLocal
from business.identity import GUEST_COOKIE_NAME, AUTH_COOKIE_NAME, new_anon_id, resolve_user
from dao.user_dao import create_guest
from utils.security import issue_token


def _new_db():
    return SessionLocal()


def test_guest_no_cookie_creates_guest_and_requests_set():
    db = _new_db()
    try:
        user, need_set = resolve_user(db, None, None)
        assert need_set is True
        assert user.is_guest is True
        assert user.device_id  # 匿名 ID 已写入 device_id
    finally:
        db.close()


def test_guest_same_cookie_reuses_user():
    gid = new_anon_id()
    db = _new_db()
    try:
        # 首次：传入 guest cookie（已存在），无需写回；复用同一游客
        u1, n1 = resolve_user(db, None, gid)
        # 第二次：同样 cookie，仍复用，且从未因"无 cookie"而生成新 ID
        u2, n2 = resolve_user(db, None, gid)
        assert n1 is False
        assert n2 is False
        assert u1.id == u2.id
    finally:
        db.close()


def test_invalid_auth_cookie_does_not_become_guest_from_that_slot():
    # 伪造的 auth cookie 不应被当成游客 device_id；应走独立 guest 分支
    db = _new_db()
    try:
        user, need_set = resolve_user(db, "not-a-jwt", None)
        assert user.is_guest is True
        assert need_set is True
    finally:
        db.close()


def test_valid_auth_cookie_returns_logged_in_user():
    db = _new_db()
    try:
        guest = create_guest(db, new_anon_id())
        guest.is_guest = False
        guest.email = "real@example.com"
        db.add(guest)
        db.commit()
        db.refresh(guest)
        token = issue_token(guest.id)
        user, need_set = resolve_user(db, token, None)
        assert need_set is False
        assert user.id == guest.id
        assert user.is_guest is False
    finally:
        db.close()


def test_forged_guest_cookie_becomes_guest_not_logged_in():
    # guest cookie 槽位伪造值 → 当作游客匿名 ID（低价值，预期行为）；
    # 关键是它只影响 guest 槽，不会污染 auth 槽。
    db = _new_db()
    try:
        user, need_set = resolve_user(db, None, "forged-guest-id")
        assert user.is_guest is True
        assert user.device_id == "forged-guest-id"
    finally:
        db.close()
