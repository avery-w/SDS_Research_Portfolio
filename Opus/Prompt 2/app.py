import os
from datetime import timedelta
from pathlib import Path

import click
from flask import Flask, g, send_from_directory, session

import core
from models import CATEGORIES, db, setting

BASE = Path(__file__).parent


def create_app(test_config=None):
    app = Flask(__name__, instance_path=str(BASE / "instance"))
    Path(app.instance_path).mkdir(exist_ok=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or _dev_secret(app.instance_path),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{Path(app.instance_path) / 'market.db'}"),
        UPLOAD_DIR=os.environ.get("UPLOAD_DIR", str(Path(app.instance_path) / "uploads")),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # uploads over 5 MB get a 413
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=14),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    from admin import bp as admin_bp
    from api import bp as api_bp
    from seller import bp as seller_bp
    from shop import bp as shop_bp
    for bp in (shop_bp, seller_bp, admin_bp, api_bp):
        app.register_blueprint(bp)
    core.register_error_handlers(app)

    @app.before_request
    def before():
        core.load_user()
        core.check_csrf()
        g.old = session.pop("old", {})

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    @app.context_processor
    def inject():
        return {"csrf_token": core.csrf_token, "old": core.old, "money": core.money,
                "setting": setting, "CATEGORIES": CATEGORIES}

    @app.get("/uploads/<path:name>")
    def upload(name):
        return send_from_directory(app.config["UPLOAD_DIR"], name, max_age=86400)

    @app.cli.command("init-db")
    def init_db():
        """Create tables."""
        db.create_all()
        click.echo("Database ready.")

    @app.cli.command("seed")
    def seed_cmd():
        """Create tables and load demo users, stores, products and orders."""
        from seed import seed
        db.create_all()
        click.echo(seed())

    with app.app_context():
        db.create_all()
    return app


def _dev_secret(folder):
    """Stable per-install secret so sessions survive restarts. Set SECRET_KEY in production."""
    p = Path(folder) / "secret_key"
    if not p.exists():
        p.write_text(os.urandom(32).hex())
    return p.read_text()


if __name__ == "__main__":
    create_app().run(debug=True)
