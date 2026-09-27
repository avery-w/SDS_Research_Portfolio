"""Demo data: `flask --app app seed`. Safe to run once on an empty database."""
import random
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

PASSWORD = "demo-pass-123"

STORES = {
    "Bevo Threads": ("seller@example.com", "Rosa Martinez", "Screen-printed tees and hoodies, hand-pulled in East Austin.", [
        ("Burnt Orange Pocket Tee", "Apparel", 2400, 40, 0.4, 12, 10, 1, "Heavyweight cotton tee with a tiny longhorn on the pocket."),
        ("Campus Tower Hoodie", "Apparel", 5800, 25, 1.3, 14, 12, 3, "Fleece hoodie with the tower lit up orange. Runs slightly large."),
        ("Guadalupe Street Cap", "Accessories", 2600, 30, 0.3, 11, 8, 5, "Unstructured six-panel cap, embroidered."),
        ("Canvas Market Tote", "Accessories", 1800, 60, 0.5, 16, 15, 1, "12 oz canvas tote, holds a week of groceries."),
    ]),
    "Speedway Prints": ("prints@example.com", "Dev Patel", "Risograph and letterpress prints of Austin landmarks.", [
        ("Tower at Dusk Riso Print", "Art & Prints", 3500, 20, 0.6, 20, 16, 1, "Two-color riso print, 11x17, signed."),
        ("Barton Springs Poster", "Art & Prints", 2800, 35, 0.5, 26, 4, 4, "18x24 screen-printed poster shipped in a tube."),
        ("Congress Bridge Bats Card Set", "Art & Prints", 1500, 80, 0.3, 7, 5, 2, "Set of 8 letterpress notecards with envelopes."),
        ("Framed Skyline Print", "Home & Living", 12000, 6, 9.0, 30, 24, 3, "24x30 framed print with UV glass. Ships boxed."),
    ]),
    "Hill Country Pantry": ("pantry@example.com", "Sam Whitaker", "Small-batch hot sauces, rubs and pecans from the Hill Country.", [
        ("Smoked Serrano Hot Sauce", "Food & Drink", 1200, 100, 0.8, 8, 3, 3, "Medium heat, oak-smoked serranos and garlic."),
        ("Brisket Rub Trio", "Food & Drink", 2400, 50, 1.5, 9, 6, 4, "Salt-and-pepper, coffee, and ancho rubs."),
        ("Candied Texas Pecans", "Food & Drink", 1600, 70, 1.0, 8, 6, 3, "One pound of cinnamon-candied pecans."),
        ("Cast Iron Skillet 12in", "Home & Living", 6500, 15, 8.0, 20, 13, 4, "Pre-seasoned 12 inch skillet, a Texas kitchen staple."),
    ]),
    "Congress Ave Tech": ("tech@example.com", "Jordan Lee", "Desk gear and gadgets for students and makers.", [
        ("Mechanical Keyboard (Orange Keycaps)", "Electronics", 11900, 12, 2.4, 18, 7, 3, "Hot-swappable 75% board, tactile switches."),
        ("USB-C Dock 8-in-1", "Electronics", 7900, 25, 0.6, 7, 5, 2, "HDMI 4K60, 100W passthrough, SD reader."),
        ("Standing Desk Frame", "Home & Living", 32900, 5, 62.0, 50, 24, 8, "Dual-motor frame. Heavy: ships with UPS Additional Handling."),
        ("Noise-Canceling Headphones", "Electronics", 14900, 18, 1.2, 9, 8, 4, "40-hour battery, great for the PCL."),
    ]),
}
CUSTOMERS = [("customer@example.com", "Alex Kim", "2100 Speedway", "Austin", "TX", "78712"),
             ("maria@example.com", "Maria Gomez", "350 5th Ave", "New York", "NY", "10118"),
             ("chris@example.com", "Chris Park", "1 Market St", "San Francisco", "CA", "94105"),
             ("taylor@example.com", "Taylor Brooks", "400 Broad St", "Seattle", "WA", "98109")]


def seed(db):
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        print("Database already has users; skipping seed.")
        return
    rnd = random.Random(42)
    pw = generate_password_hash(PASSWORD)
    db.execute("INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, 'admin')",
               ("admin@example.com", pw, "Avery Admin"))
    customers = [db.execute("INSERT INTO users (email, password_hash, name, role, street, city, state, zip) "
                            "VALUES (?, ?, ?, 'customer', ?, ?, ?, ?)", (e, pw, n, *addr)).lastrowid
                 for e, n, *addr in CUSTOMERS]
    products = []
    for store, (email, name, desc, items) in STORES.items():
        uid = db.execute("INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, 'seller')",
                         (email, pw, name)).lastrowid
        sid = db.execute("INSERT INTO stores (seller_id, name, description) VALUES (?, ?, ?)",
                         (uid, store, desc)).lastrowid
        for pname, cat, price, stock, wt, l, w, h, pdesc in items:
            pid = db.execute("INSERT INTO products (store_id, name, description, category, price_cents, stock, "
                             "weight_lb, length_in, width_in, height_in) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (sid, pname, pdesc, cat, price, stock, wt, l, w, h)).lastrowid
            products.append((pid, sid, pname, price))

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    statuses = ["delivered"] * 6 + ["shipped"] * 2 + ["placed", "cancelled", "return_requested", "returned"]
    for n in range(70):
        created = now - timedelta(days=rnd.randint(0, 29), hours=rnd.randint(0, 23))
        pid, sid, pname, price = rnd.choice(products)
        qty = rnd.randint(1, 3)
        cid = rnd.choice(customers)
        cust = db.execute("SELECT * FROM users WHERE id = ?", (cid,)).fetchone()
        status = rnd.choice(statuses)
        sub = price * qty
        ship = rnd.choice([1150, 1390, 2480, 3900])
        tax = round(sub * 0.0825)
        ts = created.strftime("%Y-%m-%d %H:%M:%S")
        delivered = (created + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S") \
            if status in ("delivered", "return_requested", "returned") else None
        oid = db.execute(
            "INSERT INTO orders (checkout_ref, customer_id, store_id, status, subtotal_cents, shipping_cents, "
            "tax_cents, total_cents, ship_service, tracking, ship_name, ship_street, ship_city, ship_state, ship_zip, "
            "return_reason, delivered_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'UPS Ground', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"FA-DEMO{n:03d}", cid, sid, status, sub, ship, tax, sub + ship + tax,
             None if status in ("placed", "cancelled") else f"1Z{rnd.randrange(16**16):016X}",
             cust["name"], cust["street"], cust["city"], cust["state"], cust["zip"],
             "Arrived in the wrong size" if status.startswith("return") else None, delivered, ts)).lastrowid
        db.execute("INSERT INTO order_items (order_id, product_id, name, price_cents, qty) VALUES (?, ?, ?, ?, ?)",
                   (oid, pid, pname, price, qty))
        db.execute("INSERT INTO events (actor_id, entity, entity_id, action, note, created_at) "
                   "VALUES (?, 'order', ?, 'placed', 'UPS Ground', ?)", (cid, oid, ts))
        if status != "placed":
            db.execute("INSERT INTO events (entity, entity_id, action, created_at) VALUES ('order', ?, ?, ?)",
                       (oid, status, delivered or ts))

    conv = db.execute("INSERT INTO conversations (customer_id, store_id) VALUES (?, 1)", (customers[0],)).lastrowid
    db.execute("INSERT INTO messages (conversation_id, sender_id, body, product_id) VALUES (?, ?, ?, 2)",
               (conv, customers[0], "Hi! Does the Campus Tower Hoodie run true to size? I'm usually a medium."))
    db.execute("INSERT INTO messages (conversation_id, sender_id, body) VALUES (?, 2 + ?, ?)",
               (conv, len(CUSTOMERS), "It runs a little roomy. If you like a fitted look, go with a small!"))
    db.commit()
    print(f"Seeded demo data. Every account uses the password {PASSWORD!r}:")
    print("  admin@example.com (admin), seller@example.com (seller), customer@example.com (customer)")
