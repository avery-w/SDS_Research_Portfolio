import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.security import (  # noqa: E402
    create_session_token,
    hash_password,
    read_session_token,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_session_token_roundtrip_and_tampering():
    token = create_session_token(42)
    assert read_session_token(token) == 42
    assert read_session_token(token + "tampered") is None
    assert read_session_token("garbage") is None


if __name__ == "__main__":
    test_password_hash_roundtrip()
    test_session_token_roundtrip_and_tampering()
    print("ok")
