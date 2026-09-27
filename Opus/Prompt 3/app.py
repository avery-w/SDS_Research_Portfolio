import os
from pathlib import Path

import click
from flask import Flask, render_template
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, select
from werkzeug.security import generate_password_hash

import admin
import auth
import chatbot
import seller
import shop
from models import Message, User, db, get_setting

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],  # fail fast if missing
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///marketplace.db"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    UPLOAD_DIR=str(Path(app.root_path) / "static" / "uploads"),
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
db.init_app(app)
CSRFProtect(app)
auth.login_manager.init_app(app)
auth.limiter.init_app(app)
for module in (auth, shop, seller, admin, chatbot):
    app.register_blueprint(module.bp)


@app.after_request
def security_headers(resp):
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
    )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    return resp


@app.template_filter("money")
def money(cents):
    return f"${(cents or 0) / 100:,.2f}"


@app.context_processor
def globals_():
    unread = 0
    if current_user.is_authenticated:
        unread = db.session.scalar(select(func.count(Message.id)).filter_by(recipient_id=current_user.id, read=False))
    return {"site_name": get_setting("site_name"), "chatbot_on": get_setting("chatbot_enabled") == "1", "unread": unread}


@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
@app.errorhandler(429)
def error_page(e):
    return render_template("error.html", e=e), e.code


@app.cli.command("init-db")
def init_db():
    """Create all tables."""
    db.create_all()
    click.echo("Database ready.")


@app.cli.command("create-admin")
@click.argument("email")
@click.option("--name", default="Admin")
@click.password_option()
def create_admin(email, name, password):
    """Create an admin account (the only way to get one)."""
    auth.check_password(password)
    db.session.add(User(email=email.lower(), name=name, role="admin", password_hash=generate_password_hash(password)))
    db.session.commit()
    click.echo(f"Admin {email} created.")
