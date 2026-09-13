"""Minimal smoke test for the money/security-critical paths: registration,
role gating, cart -> checkout -> shipping rate -> order placement, and order
status rollup. Run: python test_app.py
"""
import re

from app import create_app
from app.extensions import db
from app.models import User, Store, Product, ROLE_SELLER


class TestConfig:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "/tmp/marketplace_test_uploads"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    SHIP_FROM_ADDRESS = {
        "name": "Test",
        "address": "110 Inner Campus Drive",
        "city": "Austin",
        "state": "TX",
        "zip": "78705",
        "country": "US",
    }
    UPS_CLIENT_ID = None
    UPS_CLIENT_SECRET = None
    UPS_ACCOUNT_NUMBER = None
    UPS_ENV = "test"
    ANTHROPIC_API_KEY = None
    WTF_CSRF_ENABLED = False


def _extract_csrf_free():
    return {}


def demo():
    app = create_app(TestConfig)
    client = app.test_client()

    with app.app_context():
        seller = User(email="seller@test.com", name="Seller", role=ROLE_SELLER)
        seller.set_password("password123")
        db.session.add(seller)
        db.session.flush()
        store = Store(seller_id=seller.id, name="Test Store")
        db.session.add(store)
        db.session.flush()
        product = Product(store_id=store.id, name="Widget", price=10.00, weight_oz=16, stock_qty=5)
        db.session.add(product)
        db.session.commit()
        product_id = product.id

    # Register a customer
    resp = client.post(
        "/register",
        data={"name": "Cust", "email": "cust@test.com", "password": "password123", "role": "customer"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    # Seller-only page should 403 a customer
    resp = client.get("/seller/dashboard")
    assert resp.status_code == 403, "customer should not access seller dashboard"

    # Add to cart
    resp = client.post(f"/cart/add/{product_id}", data={"quantity": "2"}, follow_redirects=True)
    assert resp.status_code == 200

    resp = client.get("/cart")
    assert b"Widget" in resp.data
    assert b"20.00" in resp.data  # subtotal 2 x $10

    # Shipping rate fallback estimator (no UPS creds configured)
    resp = client.post(
        "/api/checkout/shipping-rates",
        json={"address": "123 Main St", "city": "Dallas", "state": "TX", "zip": "75201"},
    )
    assert resp.status_code == 200
    rates = resp.get_json()["rates"]
    assert len(rates) == 4
    assert all(r["cost"] > 0 for r in rates)
    codes = {r["code"] for r in rates}
    assert codes == {"03", "12", "02", "01"}

    # Place the order using the cheapest rate
    cheapest = min(rates, key=lambda r: r["cost"])
    resp = client.post(
        "/checkout/place-order",
        data={
            "ship_name": "Cust",
            "ship_address": "123 Main St",
            "ship_city": "Dallas",
            "ship_state": "TX",
            "ship_zip": "75201",
            "service_code": cheapest["code"],
            "service_name": cheapest["name"],
            "shipping_cost": str(cheapest["cost"]),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        product = Product.query.get(product_id)
        assert product.stock_qty == 3, "stock should decrement by ordered quantity"

        from app.models import Order

        order = Order.query.first()
        assert order is not None
        assert order.status == "pending"
        item = order.items[0]
        item.status = "delivered"
        db.session.commit()
        assert order.status == "delivered", "order status should roll up from item statuses"

    print("All checks passed.")


if __name__ == "__main__":
    demo()
