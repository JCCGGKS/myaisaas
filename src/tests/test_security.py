"""鉴权工具测试：JWT 签发/校验，以及密码 bcrypt 哈希。"""
from utils.security import hash_password, issue_token, verify_password, verify_token


def test_issue_verify_roundtrip():
    token = issue_token(7)
    assert token.startswith("eyJ")  # JWT 头 base64url 编码固定前缀
    assert verify_token(token) == 7


def test_verify_rejects_non_jwt():
    # 游客 device_id、任意字符串、空串均不是合法 JWT
    assert verify_token("dev_abc123") is None
    assert verify_token("not-a-jwt") is None
    assert verify_token("") is None


def test_verify_rejects_tampered():
    token = issue_token(7)
    bad = token[:-3] + "xxx"  # 篡改签名
    assert verify_token(bad) is None


def test_issue_carries_guest_flag():
    token = issue_token(3, is_guest=True)
    # 校验通过且能还原 user_id
    assert verify_token(token) == 3


# ---------- 密码哈希（bcrypt） ----------

def test_hash_password_is_bcrypt_and_not_plaintext():
    h = hash_password("secret123")
    assert h != "secret123"          # 绝不存明文
    assert h.startswith("$2")        # bcrypt 哈希前缀
    assert len(h) == 60


def test_verify_password_correct_and_wrong():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True
    assert verify_password("wrong", h) is False


def test_verify_password_handles_empty_hash():
    assert verify_password("anything", None) is False
    assert verify_password("anything", "") is False

