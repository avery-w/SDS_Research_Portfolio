"""Run with: python -m pytest tests  (or: python tests/test_app.py)"""

import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop("ANTHROPIC_API_KEY", None)  # chat falls back to the offline answer

from marketplace import create_app
from marketplace.models import Order, Product, User, db, sales_summary
from marketplace.seed import DEMO_PASSWORD, seed_demo
from marketplace.shipping import Package, ShippingError, estimate_rates, zone_for

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def test_ups_rules():
    # Dimensional weight: 20*20*20/139 = 57.6 -> 58 lb beats 10 lb actual.
    assert Package(10, 20, 20, 20).billable_weight() == 58
    # Actual weight rounds up to the next pound.
    assert Package(2.1, 6, 6, 6).billable_weight() == 3
    # Large package (length > 96 in) bills at least 90 lb.
    assert Package(20, 97, 10, 5).billable_weight() == 90
    for too_big in (Package(151, 10, 10, 10), Package(10, 109, 5, 5), Package(10, 100, 20, 20)):
        try:
            too_big.check_limits()
            raise AssertionError("expected ShippingError")
        except ShippingError:
            pass
    assert zone_for("TX") == 2 and zone_for("OK") == 4 and zone_for("NY") == 7 and zone_for("ME") == 8
    rates = estimate_rates([Package(2, 10, 8, 4)], "NY")
    assert rates["03"][0] < rates["12"][0] < rates["02"][0] < rates["01"][0]
    assert rates["01"][1] == 1


def login(client, email):
    client.post("/logout")
    return client.post("/login", data={"email": email, "password": DEMO_PASSWORD})


def test_marketplace_flow():
    uploads = tempfile.mkdtemp()
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "SQLALCHEMY_DATABASE_URI": "sqlite://", "UPLOAD_FOLDER": uploads, "SECRET_KEY": "test"})
    c = app.test_client()
    with app.app_context():
        db.create_all()
        seed_demo()
        mug = db.session.scalar(db.select(Product).filter_by(name="Ceramic Coffee Mug"))
        mug_id, mug_stock = mug.id, mug.stock

    # Seller adds a product with an image; a disguised non-image is rejected.
    login(c, "seller@example.com")
    form = {"name": "Poster", "price": "12.50", "stock": "3", "weight_lb": "0.5", "length_in": "24", "width_in": "3", "height_in": "3", "active": "1"}
    assert c.post("/seller/products/new", data={**form, "image": (io.BytesIO(b"<script>"), "x.png")}).status_code == 400
    assert c.post("/seller/products/new", data={**form, "image": (io.BytesIO(PNG), "p.png")}).status_code == 302

    # Customer browses, searches, adds to cart, gets rates, checks out.
    login(c, "customer@example.com")
    assert b"Poster" in c.get("/?q=poster").data
    c.post(f"/cart/{mug_id}", data={"quantity": 2, "mode": "add"})
    addr = {"name": "Demo", "street": "350 5th Ave", "city": "New York", "state": "NY", "zip": "10118"}
    rates = c.post("/api/shipping/rates", json=addr).get_json()
    assert rates["source"] == "estimate" and rates["services"][0]["code"] == "03"
    assert c.post("/api/shipping/rates", json={**addr, "zip": "abc"}).status_code == 400
    resp = c.post("/api/checkout", json={**addr, "service_code": "03"})
    assert resp.status_code == 201, resp.get_json()
    order_id = resp.get_json()["order_ids"][0]
    with app.app_context():
        assert db.session.get(Product, mug_id).stock == mug_stock - 2
        assert db.session.get(Order, order_id).shipping_cents == rates["services"][0]["amount_cents"]
    assert c.post("/api/checkout", json={**addr, "service_code": "03"}).status_code == 400  # cart now empty

    # Chat answers offline and points to the seller.
    chat = c.post("/api/chat", json={"messages": [{"role": "user", "content": "do you sell a coffee mug?"}]}).get_json()
    assert any("Message" in link["label"] for link in chat["links"])
    assert c.post("/api/chat", json={"messages": [{"role": "assistant", "content": "hi"}]}).status_code == 400

    # Customer cancels, stock comes back; customers can't reach seller/admin pages.
    c.post(f"/orders/{order_id}/cancel")
    with app.app_context():
        assert db.session.get(Order, order_id).status == "cancelled"
        assert db.session.get(Product, mug_id).stock == mug_stock
    assert c.get("/admin/").status_code == 403 and c.get("/seller/").status_code == 403

    # Admin reopens the order (stock taken again), sees analytics, deactivates the seller.
    login(c, "admin@example.com")
    c.post(f"/admin/orders/{order_id}", data={"status": "placed"})
    assert b"Sales analytics" in c.get("/admin/").data
    with app.app_context():
        assert db.session.get(Product, mug_id).stock == mug_stock - 2
        assert sales_summary()["orders"] == 1
        seller_id = db.session.scalar(db.select(User.id).filter_by(email="seller@example.com"))
    c.post(f"/admin/users/{seller_id}", data={"role": "seller", "active": "0"})
    assert c.get(f"/product/{mug_id}").status_code == 404  # deactivated seller's listings vanish
    assert b"deactivated" in login(c, "seller@example.com").data


if __name__ == "__main__":
    test_ups_rules()
    test_marketplace_flow()
    print("all tests passed")
