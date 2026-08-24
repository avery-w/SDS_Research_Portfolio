from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate

from app.config import Config
from app.extensions import db
from app.models import User
from app.routes.admin import admin_bp
from app.routes.api import api_bp
from app.routes.auth import auth_bp
from app.routes.customer import customer_bp
from app.routes.seller import seller_bp

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
migrate = Migrate()


def seed_data():
    if User.query.first() is not None:
        return

    admin = User(name="Platform Admin", email="admin@market.local", role="admin")
    admin.set_password("admin123")

    seller = User(name="Seller User", email="seller@market.local", role="seller")
    seller.set_password("seller123")

    customer = User(name="Customer User", email="customer@market.local", role="customer")
    customer.set_password("customer123")

    db.session.add_all([admin, seller, customer])
    db.session.commit()

    store = Store(name="Austin Goods Co.", description="Popular products for everyday life.", owner_id=seller.id)
    db.session.add(store)
    db.session.commit()

    products = [
        Product(name="Organic Coffee Beans", description="Roasted in small batches with rich cocoa notes.", price=18.99, stock=42, category="Food", image_url="/static/images/default.png", seller_id=seller.id, store_id=store.id),
        Product(name="Ergo Standing Desk", description="Adjustable workstation for better posture.", price=349.00, stock=8, category="Office", image_url="/static/images/default.png", seller_id=seller.id, store_id=store.id),
        Product(name="Yoga Wellness Mat", description="Non-slip mat made from recycled materials.", price=39.50, stock=16, category="Fitness", image_url="/static/images/default.png", seller_id=seller.id, store_id=store.id),
    ]
    db.session.add_all(products)
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        seed_data()

    return app
