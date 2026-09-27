import os
import secrets
from decimal import Decimal, InvalidOperation

import click
from flask import Flask, render_template
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

from .models import SETTING_DEFAULTS, Message, Setting, User, db, get_setting

login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user if user and user.active else None  # deactivation logs the user out on the next request


def to_cents(text):
    """'12.34' -> 1234. Raises ValueError on bad or negative input."""
    try:
        value = Decimal(str(text).strip().lstrip("$"))
    except InvalidOperation:
        raise ValueError("Enter a valid price") from None
    if value < 0 or value != value.quantize(Decimal("0.01")):
        raise ValueError("Enter a valid price")
    return int(value * 100)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(app.instance_path, 'marketplace.db')}"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        UPLOAD_FOLDER=os.path.join(app.static_folder, "uploads"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        UPS_CLIENT_ID=os.environ.get("UPS_CLIENT_ID", ""),
        UPS_CLIENT_SECRET=os.environ.get("UPS_CLIENT_SECRET", ""),
        UPS_ACCOUNT_NUMBER=os.environ.get("UPS_ACCOUNT_NUMBER", ""),
        UPS_BASE_URL=os.environ.get("UPS_BASE_URL", "https://wwwcie.ups.com"),
        UPS_API_VERSION=os.environ.get("UPS_API_VERSION", "v2409"),
        CHAT_MODEL=os.environ.get("CHAT_MODEL", "claude-opus-5"),
    )
    if test_config:
        app.config.update(test_config)
    elif not os.environ.get("SECRET_KEY"):
        app.logger.warning("SECRET_KEY not set; sessions will reset on restart")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import admin, api, auth, seller, shop

    for module in (auth, shop, seller, admin, api):
        app.register_blueprint(module.bp)

    app.jinja_env.filters["money"] = lambda cents: f"${(cents or 0) / 100:,.2f}"

    @app.context_processor
    def globals_():
        unread = 0
        if current_user.is_authenticated:
            unread = db.session.query(Message).filter_by(recipient_id=current_user.id, read=False).count()
        return {"site_name": get_setting("site_name"), "announcement": get_setting("announcement"), "unread": unread}

    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def error(e):
        return render_template("error.html", error=e), e.code

    @app.cli.command("init-db")
    @click.option("--seed", is_flag=True, help="Add demo users, a store and products.")
    def init_db(seed):
        """Create all tables and default platform settings."""
        db.create_all()
        for key, value in SETTING_DEFAULTS.items():
            if not db.session.get(Setting, key):
                db.session.add(Setting(key=key, value=value))
        db.session.commit()
        if seed:
            from .seed import seed_demo

            seed_demo()
        click.echo("Database ready.")

    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("name")
    @click.password_option()
    def create_admin(email, name, password):
        """Create an admin account."""
        user = User(email=email.lower(), name=name, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin {email} created.")

    return app
