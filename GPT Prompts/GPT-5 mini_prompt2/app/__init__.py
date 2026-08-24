from flask import Flask

from app.config import Config
from app.extensions import db, login_manager
from app.models import User
from app.routes.admin import admin_bp
from app.routes.api import api_bp
from app.routes.auth import auth_bp
from app.routes.customer import customer_bp
from app.routes.seller import seller_bp


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

    store = seller.create_store(name="Austin Goods Co.", description="Everyday essentials and local favorites.")
    db.session.add(store)
    db.session.commit()

    products = [
        {
            "name": "Organic Coffee Blend",
            "description": "Small-batch roasted beans with cocoa and caramel notes.",
            "price": 18.99,
            "stock": 35,
            "category": "Food",
            "image_url": "/static/images/coffee.png",
        },
        {
            "name": "Premium Yoga Mat",
            "description": "Non-slip, eco-friendly mat designed for daily workouts.",
            "price": 42.50,
            "stock": 18,
            "category": "Wellness",
            "image_url": "/static/images/mat.png",
        },
        {
            "name": "Smart Desk Lamp",
            "description": "Touch-controlled lamp with warm and cool settings.",
            "price": 59.00,
            "stock": 12,
            "category": "Home",
            "image_url": "/static/images/lamp.png",
        },
    ]

    for item in products:
        product = seller.create_product(store_id=store.id, **item)
        db.session.add(product)

    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

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
