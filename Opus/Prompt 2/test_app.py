"""End-to-end check of the auth/role/error contract and the money paths. Run: python test_app.py"""
import os
import re
import tempfile

os.environ["CHATBOT_OFFLINE"] = "1"

from app import create_app  # noqa: E402
from models import OrderItem, Product, db  # noqa: E402
from seed import seed  # noqa: E402


def client_for(app, email=None):
    c = app.test_client()
    if email:
        c.get("/login")
        r = c.post("/login", data={"email": email, "password": "password123", "csrf_token": token(c)})
        assert r.status_code == 302, (email, r.status_code)
    return c


def token(c):
    return re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").get_data(as_text=True)).group(1)


def test_marketplace():
    tmp = tempfile.mkdtemp()
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp}/t.db", "UPLOAD_DIR": tmp})
    with app.app_context():
        seed()
        pid = Product.query.filter(Product.stock >= 12).first().id
    anon, cust = client_for(app), client_for(app, "customer@longhorn.market")
    seller, admin = client_for(app, "seller1@longhorn.market"), client_for(app, "admin@longhorn.market")

    # missing auth: HTML redirects to login, API returns 401
    assert anon.get("/cart").status_code == 302 and "/login" in anon.get("/cart").location
    assert anon.get("/admin").status_code == 302
    assert anon.get("/api/cart").status_code == 401
    assert anon.post("/api/checkout", json={}).status_code == 401
    # wrong role: 403 on both surfaces
    assert cust.get("/admin").status_code == 403 and cust.get("/seller").status_code == 403
    assert seller.get("/api/cart").status_code == 403 and admin.get("/cart").status_code == 403
    # CSRF: HTML form without token is refused; API refuses non-JSON writes
    assert cust.post("/cart/add", data={"product_id": pid, "qty": 1}).status_code == 400
    assert cust.post("/api/cart", data="product_id=1").status_code == 415
    assert cust.post("/api/cart", data="{bad json", content_type="application/json").status_code == 400
    # invalid input: API 400 with per-field errors; HTML 303 back
    r = cust.post("/api/cart", json={"product_id": "x", "qty": 0})
    assert r.status_code == 400 and set(r.json["fields"]) == {"product_id", "qty"}
    r = cust.post("/cart/add", data={"product_id": pid, "qty": "abc", "csrf_token": token(cust)},
                  headers={"Referer": f"http://localhost/products/{pid}"})
    assert r.status_code == 303 and r.location.endswith(f"/products/{pid}")
    assert cust.post("/api/cart", json={"product_id": 99999, "qty": 1}).status_code == 404
    assert cust.post("/api/cart", json={"product_id": pid, "qty": 99}).status_code == 409  # over stock

    # shipping quotes (public with explicit items)
    q = anon.post("/api/shipping/rates", json={"zip": "10001", "items": [{"product_id": pid, "qty": 1}]}).json
    assert q["origin"]["zip"] == "78705" and q["zone"] == 7 and len(q["options"]) == 4
    assert anon.post("/api/shipping/rates", json={"zip": "10001"}).status_code == 401
    assert anon.post("/api/shipping/rates", json={"zip": "ABCDE", "items": []}).status_code == 400

    # checkout decrements stock atomically and empties the cart
    with app.app_context():
        before = db.session.get(Product, pid).stock
    assert cust.post("/api/cart", json={"product_id": pid, "qty": 2}).status_code == 201
    assert cust.post("/api/checkout", json={"name": "A", "street": "2400 Nueces St", "city": "Austin",
                                            "state": "TX", "zip": "78705", "service": "XXX"}).status_code == 400
    r = cust.post("/api/checkout", json={"name": "A", "street": "2400 Nueces St", "city": "Austin",
                                         "state": "TX", "zip": "78705", "service": "2DA"})
    assert r.status_code == 201, r.json
    order = r.json
    with app.app_context():
        assert db.session.get(Product, pid).stock == before - 2
    assert cust.get("/api/cart").json["items"] == []
    assert cust.post("/api/checkout", json={"name": "A", "street": "2400 Nueces", "city": "Austin",
                                            "state": "TX", "zip": "78705", "service": "GND"}).status_code == 409

    # other users can't see the order (404, not 403, so existence isn't leaked)
    other = client_for(app, "sam@longhorn.market")
    assert other.get(f"/api/orders/{order['id']}").status_code == 404
    assert admin.get(f"/api/orders/{order['id']}").status_code == 200

    # seller of another store can't touch the item; the right seller can ship it
    item_id = order["items"][0]["id"]
    with app.app_context():
        store_owner = db.session.get(OrderItem, item_id).store.owner.email
    wrong = next(e for e in ("seller1@longhorn.market", "seller2@longhorn.market") if e != store_owner)
    s_wrong, s_right = client_for(app, wrong), client_for(app, store_owner)
    assert s_wrong.post(f"/order-items/{item_id}/shipped", data={"csrf_token": token(s_wrong)}).status_code == 404
    assert s_right.post(f"/order-items/{item_id}/delivered", data={"csrf_token": token(s_right)}).status_code == 409
    assert s_right.post(f"/order-items/{item_id}/shipped", data={"csrf_token": token(s_right)}).status_code == 302

    # shipped orders can't be cancelled; returns need delivery first
    assert cust.post(f"/api/orders/{order['id']}/cancel", json={}).status_code == 409
    assert cust.post(f"/api/order-items/{item_id}/return", json={"reason": "Too small"}).status_code == 409
    s_right.post(f"/order-items/{item_id}/delivered", data={"csrf_token": token(s_right)})
    assert cust.post(f"/api/order-items/{item_id}/return", json={"reason": "x"}).status_code == 400
    assert cust.post(f"/api/order-items/{item_id}/return", json={"reason": "Too small"}).status_code == 200
    s_right.post(f"/order-items/{item_id}/returned", data={"csrf_token": token(s_right)})
    with app.app_context():
        assert db.session.get(Product, pid).stock == before  # restocked on approved return

    # admin override + deactivation signs the user out on their next request
    assert admin.post(f"/admin/order-items/{item_id}/status",
                      data={"status": "delivered", "csrf_token": token(admin)}).status_code == 302
    with app.app_context():
        assert db.session.get(Product, pid).stock == before - 2  # override re-reserved stock
        cust_id = db.session.execute(db.text("select id from user where email='customer@longhorn.market'")).scalar()
    assert admin.post(f"/admin/users/{cust_id}", data={"action": "deactivate", "csrf_token": token(admin)}).status_code == 302
    assert cust.get("/api/cart").status_code == 401

    # chatbot validates history and answers (offline mode here)
    assert anon.post("/api/chat", json={"messages": [{"role": "assistant", "content": "hi"}]}).status_code == 400
    r = anon.post("/api/chat", json={"messages": [{"role": "user", "content": "do you have a tent?"}]})
    assert r.status_code == 200 and r.json["actions"] and "/messages/new" in r.json["actions"][0]["url"]

    # every page renders for its role
    for c, urls in ((admin, ["/admin", "/admin/users", "/admin/stores", "/admin/products", "/admin/orders",
                             "/admin/settings", "/admin/audit", "/messages", f"/orders/{order['id']}"]),
                    (s_right, ["/seller", "/seller/products", "/seller/orders", "/seller/store",
                               "/seller/products/new", "/messages"]),
                    (other, ["/", "/cart", "/orders", "/account", "/messages", "/products?q=mug",
                             "/messages/new?store_id=1&product_id=1"])):
        for u in urls:
            assert c.get(u).status_code == 200, u
    print("all marketplace checks passed")


if __name__ == "__main__":
    test_marketplace()
