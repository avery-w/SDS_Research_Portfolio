"""Flask extension singletons.

Kept in a dedicated module so that models, blueprints and services can import
them without creating a circular dependency on the application factory.
"""

from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base shared by every model."""


db = SQLAlchemy(model_class=Base)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Sign in to continue."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"

csrf = CSRFProtect()
mail = Mail()


def _rate_limit_key() -> str:
    """Rate limit by authenticated user id when available, else by IP."""

    from flask_login import current_user

    try:
        if current_user.is_authenticated:
            return f"user:{current_user.get_id()}"
    except Exception:  # pragma: no cover - defensive, request context missing
        pass
    return get_remote_address()


limiter = Limiter(key_func=_rate_limit_key)
