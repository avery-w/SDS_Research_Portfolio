"""End-to-end checks for auth, roles, validation, shipping, checkout, orders, messaging, admin and chat.

Run: python test_app.py   (or pytest test_app.py)
"""
import io
import os
import re
import tempfile

os.environ["DATABASE"] = os.path.join(tempfile.mkdtemp(), "test.db")

import chatbot  # noqa: E402
import shipping  # noqa: E402
from app import app, get_db  # noqa: E402
from seed import PASSWORD, seed  # noqa: E402

chatbot._client = False  # never call the real API from tests
app.config["UPLOAD_FOLDER"] = tempfile.mkdtemp()
with app.app_context():
    seed(get_db())


def client(email=None):
    c = app.test_client()
    if email:
        r = c.post("/login", data={"email": email, "password": PASSWORD, "csrf_token": token(c)})
        assert r.status_code == 302, r.status_code
    return c


def token(c):
    return re.search(r'name="csrf-token" content="([^"]+)"', c.get("/login").get_data(as_text=True)).group(1)


def post(c, url, **data):
    return c.post(url, data={**data, "csrf_token": token(c)})


def test_shipping_engine():
    assert shipping.zone_for("78705")[0] == 2
    assert shipping.zone_for("75201")[0] == 3      # Dallas ~180 mi
    assert shipping.zone_for("10001")[0] == 7      # New York ~1500 mi
    assert shipping.zone_for("96813")[0] == "HI"
    for bad in ("7870", "abcde", "00901"):         # short, non-numeric, Puerto Rico
        try:
            shipping.zone_for(bad)
            raise AssertionError(bad)
        except shipping.ShippingError:
            pass
    box = {"weight_lb": 2, "length_in": 10, "width_in": 8, "height_in": 6, "qty": 1}
    near = shipping.quote("78705", [box], fuel_pct=0, residential_fee=0)
    far = shipping.quote("10001", [box], fuel_pct=0, residential_fee=0)
    ground = lambda q: next(s for s in q["services"] if s["code"] == "03")["cents"]
    assert ground(far) > ground(near)
    assert near["packages"][0]["billable_lb"] == 4  # dim weight: 10*8*6/139 -> 4 lb beats 2 lb actual
    heavy = shipping.quote("78705", [{**box, "weight_lb": 60}], fuel_pct=0, residential_fee=0)
    assert "Additional Handling (weight)" in heavy["packages"][0]["surcharges"]
    assert len(shipping.pack([{**box, "weight_lb": 100, "qty": 2}])) == 2  # 150 lb cap splits boxes
    hi = shipping.quote("96813", [box], fuel_pct=0, residential_fee=0)
    assert "03" not in [s["code"] for s in hi["services"]]  # no Ground to Hawaii
    try:
        shipping.check_item(151, 1, 1, 1)
        raise AssertionError
    except shipping.ShippingError:
        pass


def test_auth_and_roles():
    anon = app.test_client()
    assert anon.get("/cart").status_code == 302                       # missing auth -> login
    assert anon.post("/api/checkout", json={}).status_code == 401    # API: JSON 401
    assert anon.post("/cart/add", data={"product_id": 1}).status_code == 400  # no CSRF token
    cust, seller = client("customer@example.com"), client("seller@example.com")
    assert cust.get("/admin").status_code == 403
    assert cust.get("/seller").status_code == 403
    assert seller.get("/cart").status_code == 403
    assert seller.get("/seller").status_code == 200
    assert seller.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 403
    bad = app.test_client()
    r = bad.post("/login", data={"email": "customer@example.com", "password": "nope", "csrf_token": token(bad)})
    assert r.status_code == 302 and "Invalid email or password" in bad.get("/login").get_data(as_text=True)


def test_register_validation():
    c = app.test_client()
    assert post(c, "/register", name="X", email="bad", password="longenough", role="customer").status_code == 302
    assert "Email is not valid" in c.get("/register").get_data(as_text=True)
    post(c, "/register", name="Shop", email="new@example.com", password="short", role="seller", store_name="S")
    assert "at least 8" in c.get("/register").get_data(as_text=True)
    r = post(c, "/register", name="New Seller", email="new@example.com", password="longenough", role="seller",
             store_name="Brand New Shop")
    assert r.headers["Location"].endswith("/seller")


def test_checkout_and_order_lifecycle():
    cust = client("customer@example.com")
    with app.app_context():
        stock_before = get_db().execute("SELECT stock FROM products WHERE id = 1").fetchone()[0]
    assert post(cust, "/cart/add", product_id=1, qty=2).status_code == 302
    assert post(cust, "/cart/add", product_id=1, qty=999).status_code == 302  # over stock -> flash, not added
    assert post(cust, "/cart/add", product_id=99999).status_code == 404
    assert post(cust, "/cart/add", product_id=5, qty=1).status_code == 302  # second store

    r = cust.post("/api/shipping/rates", json={"zip": "10001"})
    assert r.status_code == 200 and len(r.json["shipments"]) == 2 and r.json["destination"]["zone"] == 7
    assert cust.post("/api/shipping/rates", json={"zip": "nope"}).status_code == 400
    assert cust.post("/api/shipping/rates", data="zip=10001").status_code in (400, 415)
    assert app.test_client().post("/api/shipping/rates", json={"zip": "78705", "items": [{"product_id": 1, "qty": 1}]}).status_code == 200
    assert app.test_client().post("/api/shipping/rates", json={"zip": "78705", "items": [{"product_id": "1"}]}).status_code == 400

    addr = {"name": "Alex", "street": "2100 Speedway", "city": "Austin", "state": "TX", "zip": "78712"}
    assert cust.post("/api/checkout", json={**addr, "service": "99"}).status_code == 400
    assert cust.post("/api/checkout", json={**addr, "state": "ZZ", "service": "03"}).status_code == 400
    r = cust.post("/api/checkout", json={**addr, "service": "03"})
    assert r.status_code == 201, r.json
    order_ids = r.json["order_ids"]
    assert len(order_ids) == 2
    assert cust.post("/api/checkout", json={**addr, "service": "03"}).status_code == 400  # cart now empty
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0] == stock_before - 2
        o = db.execute("SELECT * FROM orders WHERE id = ?", (order_ids[0],)).fetchone()
        assert o["total_cents"] == o["subtotal_cents"] + o["shipping_cents"] + o["tax_cents"]
        assert o["tax_cents"] == round(o["subtotal_cents"] * 0.0825)

    oid = next(i for i in order_ids if client("seller@example.com").get(f"/orders/{i}").status_code == 200)
    seller, other_seller = client("seller@example.com"), client("prints@example.com")
    assert other_seller.get(f"/orders/{oid}").status_code == 403
    assert client("maria@example.com").get(f"/orders/{oid}").status_code == 403
    assert post(cust, f"/orders/{oid}/status", status="shipped").status_code == 403       # customer can't ship
    assert post(seller, f"/orders/{oid}/status", status="delivered").status_code == 409    # must ship first
    assert post(seller, f"/orders/{oid}/status", status="shipped", tracking="BAD").status_code == 302
    assert "tracking numbers" in seller.get("/seller").get_data(as_text=True)
    assert post(seller, f"/orders/{oid}/status", status="shipped", tracking="1Z999AA10123456784").status_code == 302
    assert post(seller, f"/orders/{oid}/status", status="delivered").status_code == 302
    assert post(cust, f"/orders/{oid}/status", status="return_requested").status_code == 302  # reason required
    assert post(cust, f"/orders/{oid}/status", status="return_requested", reason="Too big").status_code == 302
    assert post(seller, f"/orders/{oid}/status", status="returned").status_code == 302
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT status FROM orders WHERE id = ?", (oid,)).fetchone()[0] == "returned"
        assert db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0] == stock_before  # restocked

    # customer cancel on the other order restocks; cancelling twice is a conflict
    other = next(i for i in order_ids if i != oid)
    assert post(cust, f"/orders/{other}/status", status="cancelled").status_code == 302
    assert post(cust, f"/orders/{other}/status", status="cancelled").status_code == 302  # "already" -> flash
    assert post(cust, f"/orders/{other}/status", status="placed").status_code == 409
    admin = client("admin@example.com")
    assert post(admin, f"/orders/{other}/status", status="placed", note="Customer called").status_code == 302


def test_seller_products_and_uploads():
    seller, other = client("seller@example.com"), client("prints@example.com")
    form = dict(name="Longhorn Mug", description="Ceramic", category="Home & Living", price="14.50", stock="5",
                weight_lb="1.2", length_in="6", width_in="5", height_in="5")
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    r = seller.post("/seller/products/new", data={**form, "csrf_token": token(seller),
                                                  "image": (io.BytesIO(png), "mug.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 302
    pid = int(r.headers["Location"].rsplit("/", 1)[1])
    assert other.get(f"/seller/products/{pid}/edit").status_code == 403
    assert post(other, f"/seller/products/{pid}/stock", stock=0).status_code == 403
    assert post(seller, f"/seller/products/{pid}/stock", stock=-1).status_code == 302  # flash error
    r = seller.post("/seller/products/new", data={**form, "csrf_token": token(seller),
                                                  "image": (io.BytesIO(b"<svg onload=alert(1)>"), "x.svg")},
                    content_type="multipart/form-data")
    assert r.status_code == 302 and "Images must be" in seller.get("/seller").get_data(as_text=True)
    post(seller, "/seller/products/new", **{**form, "price": "1.999"})
    assert "at most 2 decimals" in seller.get("/seller").get_data(as_text=True)
    post(seller, "/seller/products/new", **{**form, "length_in": "100", "width_in": "40"})
    assert "can&#39;t ship by UPS" in seller.get("/seller").get_data(as_text=True)


def test_messaging():
    cust, seller, other = client("maria@example.com"), client("seller@example.com"), client("tech@example.com")
    r = post(cust, "/messages/start", store_id=1, product_id=1, body="Is this pre-shrunk?")
    cid = int(re.search(r"/messages/(\d+)", r.headers["Location"]).group(1))
    assert post(cust, "/messages/start", store_id=1, product_id=9, body="x").status_code == 302  # wrong store -> 400 flash
    assert post(cust, "/messages/start", store_id=1, body="").status_code == 302
    assert other.get(f"/messages/{cid}").status_code == 403
    assert "Is this pre-shrunk?" in seller.get(f"/messages/{cid}").get_data(as_text=True)
    assert post(seller, f"/messages/{cid}", body="Yes!").status_code == 302
    assert post(seller, "/messages/start", store_id=1, body="hi").status_code == 403  # customers start threads


def test_admin_controls():
    admin, cust = client("admin@example.com"), client("taylor@example.com")
    assert admin.get("/admin").status_code == 200
    for tab in ("users", "stores", "products", "orders", "settings", "activity"):
        assert admin.get(f"/admin?tab={tab}").status_code == 200, tab
    assert admin.get("/admin?tab=nope").status_code == 404
    with app.app_context():
        uid = get_db().execute("SELECT id FROM users WHERE email = 'taylor@example.com'").fetchone()[0]
        admin_id = get_db().execute("SELECT id FROM users WHERE email = 'admin@example.com'").fetchone()[0]
    assert post(admin, f"/admin/users/{admin_id}", action="deactivate").status_code == 302  # can't self-deactivate
    assert post(admin, f"/admin/users/{uid}", action="deactivate").status_code == 302
    assert cust.get("/orders").status_code == 302                                         # signed out
    assert post(admin, "/admin/users/99999", action="activate").status_code == 404
    assert post(admin, f"/admin/users/{uid}", action="explode").status_code == 302
    assert post(admin, "/admin/stores/2", action="deactivate").status_code == 302
    assert app.test_client().get("/?store=2").status_code == 404
    assert app.test_client().get("/products/5").status_code == 404                         # store 2's product
    assert post(admin, "/admin/settings", tax_rate_pct="abc").status_code == 302
    r = post(admin, "/admin/settings", tax_rate_pct="6.25", fuel_surcharge_pct="15", residential_fee="5",
             free_ground_over="50", return_window_days="14", platform_fee_pct="8", banner="Sale!")
    assert r.status_code == 302 and "Sale!" in app.test_client().get("/").get_data(as_text=True)
    assert post(client("customer@example.com"), "/admin/settings", tax_rate_pct="0").status_code == 403


def test_chat_fallback():
    c = app.test_client()
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "How do returns work?"}]})
    assert r.status_code == 200 and "return" in r.json["reply"].lower() and r.json["ai"] is False
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "looking for a hoodie"}]})
    assert any("Hoodie" in s["label"] for s in r.json["suggestions"])
    assert c.post("/api/chat", json={"messages": [{"role": "assistant", "content": "hi"}]}).status_code == 400
    assert c.post("/api/chat", json={"messages": "hi"}).status_code == 400
    assert c.post("/api/chat", data="x").status_code in (400, 415)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
