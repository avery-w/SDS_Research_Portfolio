"""Run: python test_app.py   (no network needed, ZIP lookup is stubbed)"""
import io
import os
import tempfile

os.environ.update(SECRET_KEY="test", DATABASE_URL="sqlite://", COOKIE_SECURE="0")

import shipping
from app import app
from models import Order, Product, User, db
from PIL import Image

shipping.zone_for_zip = lambda z: 5  # skip the GeoNames download
app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False, UPLOAD_DIR=tempfile.mkdtemp())


def login(c, email, role="customer", name="X"):
    c.post("/register", data=dict(name=name, email=email, password="correct-horse", role=role))
    return c


def png():
    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, "PNG")
    buf.seek(0)
    return buf


PRODUCT = dict(name="Mug", description="Burnt orange", price="12.50", stock="3",
               weight_lb="1.2", length_in="6", width_in="6", height_in="6", active="on")


def main():
    with app.app_context():
        db.create_all()
    seller, alice, bob, admin = (app.test_client() for _ in range(4))

    login(seller, "s@x.com", "seller")
    seller.post("/seller/", data=dict(name="Bevo Goods"))
    r = seller.post("/seller/products/new", data=dict(PRODUCT, image=(io.BytesIO(b"<script>"), "x.png")),
                    content_type="multipart/form-data")
    assert r.status_code == 400, "non-image upload must be rejected"
    r = seller.post("/seller/products/new", data=dict(PRODUCT, image=(png(), "../../evil.png")), content_type="multipart/form-data")
    assert r.status_code == 302
    with app.app_context():
        p = db.session.get(Product, 1)
        assert p.price_cents == 1250 and len(p.image) == 36 and ".." not in p.image
    assert seller.post("/seller/products/new", data=dict(PRODUCT, price="nan")).status_code == 400

    login(alice, "a@x.com")
    login(bob, "b@x.com")
    assert alice.get("/?q=mug").data.count(b"Mug") >= 1
    assert alice.get("/?q=%25").status_code == 200  # LIKE wildcard is escaped, not injected
    alice.post("/cart/add/1", data={"qty": 50})  # capped at stock
    r = alice.post("/api/checkout/rates", json={"zip": "10001"})
    rates = {x["service"]: x for x in r.get_json()["rates"]}
    # 6x6x6 in -> dim weight 2 lb; zone 5 ground = 1320 + 120 = 1440, + 585 residential, x1.15 fuel, x3 units
    assert rates["ground"]["cents"] == round(3 * (1440 + 585) * 1.15), rates["ground"]
    assert rates["ground"]["total_cents"] == 3 * 1250 + rates["ground"]["cents"]
    addr = dict(name="Alice", street="1 Main", city="Austin", state="tx", zip="78701", service="ground")
    assert seller.post("/checkout", data=addr).status_code == 403  # sellers can't buy
    alice.post("/checkout", data=addr)
    with app.app_context():
        o = db.session.get(Order, 1)
        assert o.total_cents == 3 * 1250 + rates["ground"]["cents"] and o.ship_state == "TX"
        assert db.session.get(Product, 1).stock == 0

    bob.post("/cart/add/1")
    assert bob.get("/orders/1").status_code == 404, "IDOR: other customers can't see the order"
    assert bob.post("/orders/1/status", data={"status": "cancelled"}).status_code == 404

    alice.post("/orders/1/status", data={"status": "delivered"})  # customers can't do this
    seller.post("/orders/1/status", data={"status": "shipped", "tracking": "1Z999"})
    alice.post("/orders/1/status", data={"status": "cancelled"})  # too late, already shipped
    with app.app_context():
        assert db.session.get(Order, 1).status == "shipped"
    seller.post("/orders/1/status", data={"status": "delivered"})
    alice.post("/orders/1/status", data={"status": "return_requested", "return_reason": "Chipped"})
    seller.post("/orders/1/status", data={"status": "returned"})
    with app.app_context():
        assert db.session.get(Order, 1).status == "returned"
        assert db.session.get(Product, 1).stock == 3, "approved return restocks"

    # messaging: customer -> seller ok, customer -> customer blocked
    assert alice.post("/messages/1?product=1", data={"body": "Dishwasher safe?"}).status_code == 302
    assert alice.post("/messages/3", data={"body": "hi"}).status_code == 403
    assert b"Dishwasher safe?" in seller.get("/messages/2").data

    # admin: only via CLI, can deactivate, deactivated user is logged out
    assert b"Invalid account type" in admin.post("/register", data=dict(name="A", email="z@x.com", password="correct-horse", role="admin")).data
    r = app.test_cli_runner().invoke(args=["create-admin", "root@x.com", "--password", "correct-horse-1"])
    assert r.exit_code == 0, r.output
    admin.post("/login", data=dict(email="root@x.com", password="correct-horse-1"))
    assert alice.get("/admin/").status_code == 403
    assert admin.get("/admin/?tab=analytics").status_code == 200
    admin.post("/admin/toggle/user/2")
    assert alice.get("/orders").status_code == 302, "deactivated user bounced to login"
    assert alice.post("/login", data=dict(email="a@x.com", password="correct-horse")).status_code == 401

    # chatbot input validation (no API call made)
    for bad in [None, [], [{"role": "assistant", "content": "hi"}], [{"role": "user", "content": "x" * 2001}]]:
        assert bob.post("/api/chat", json={"messages": bad}).status_code == 400

    r = bob.get("/")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    print("all tests passed")


if __name__ == "__main__":
    main()
