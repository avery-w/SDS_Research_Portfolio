import secrets

from itsdangerous import BadSignature, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_serializer = URLSafeTimedSerializer(settings.secret_key, salt="session")

SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
CSRF_COOKIE_NAME = "csrf_token"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_session_token(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def read_session_token(token: str) -> int | None:
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except BadSignature:
        return None
    return data.get("uid")


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)
