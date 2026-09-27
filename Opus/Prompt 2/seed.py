"""Demo data: `flask --app app seed`. Every account's password is password123."""
import random
from datetime import timedelta

from models import Conversation, Message, Order, OrderItem, Product, Store, User, db, now

STORES = {
    ("Maya Chen", "seller1@longhorn.market"): ("Forty Acres Outfitters", "Trail-tested gear for Texas weather", [
        ("Hill Country Daypack 22L", "Outdoors", 64.00, 1.9, (18, 12, 7), "Water-resistant ripstop pack with hydration sleeve and hip belt."),
        ("Barton Springs Insulated Bottle", "Outdoors", 29.00, 0.9, (11, 4, 4), "Keeps water cold for 24 hours. Leak-proof lid."),
        ("Enchanted Rock Camp Chair", "Outdoors", 49.50, 4.6, (22, 7, 7), "Packs down to a 22 in sack; holds 300 lb."),
        ("Pedernales Rain Shell", "Apparel", 89.00, 0.8, (12, 10, 3), "Seam-sealed 2.5-layer shell with pit zips."),
        ("Bluebonnet Trail Tee", "Apparel", 24.00, 0.3, (10, 8, 1), "Soft tri-blend tee, printed in Austin."),
        ("Guadalupe River Kayak Paddle", "Outdoors", 119.00, 2.4, (90, 8, 3), "Four-piece fiberglass paddle, 230 cm."),
        ("Lady Bird Lake Hammock", "Outdoors", 39.00, 1.2, (8, 6, 5), "Parachute nylon hammock with tree straps."),
        ("Big Bend Two-Person Tent", "Outdoors", 199.00, 6.8, (24, 8, 8), "Freestanding 3-season tent with two vestibules."),
    ]),
    ("Jordan Reyes", "seller2@longhorn.market"): ("Tower Tech Co.", "Gadgets we actually use", [
        ("Speedway Wireless Earbuds", "Electronics", 79.00, 0.4, (5, 4, 2), "ANC earbuds with 30-hour battery case."),
        ("Congress Ave Mechanical Keyboard", "Electronics", 129.00, 2.2, (18, 6, 2), "Hot-swap 75% board with tactile switches."),
        ("Sixth Street Bluetooth Speaker", "Electronics", 59.00, 1.3, (8, 4, 4), "IP67 waterproof speaker with 16-hour playtime."),
        ("PCL Study Lamp", "Home", 44.00, 3.1, (16, 8, 6), "Dimmable LED desk lamp with USB-C charging."),
        ("Dorm Power Tower", "Electronics", 34.00, 1.5, (10, 5, 5), "Surge-protected tower with 8 outlets and 4 USB ports."),
        ("27in 4K Monitor", "Electronics", 329.00, 14.5, (30, 20, 8), "IPS panel, USB-C 65W, height-adjustable stand."),
        ("Robotics Starter Kit", "Toys", 69.00, 2.0, (14, 10, 4), "Build and code six robots. Ages 10+."),
    ]),
    ("Priya Patel", "seller3@longhorn.market"): ("Eastside Pantry & Home", "Small-batch goods from East Austin", [
        ("Cold Brew Coffee Beans 2 lb", "Grocery", 26.00, 2.1, (9, 6, 4), "Medium roast, roasted on Tuesdays."),
        ("Smoked Brisket Rub", "Grocery", 12.00, 0.5, (4, 3, 3), "Salt, pepper, and a little secret. 8 oz."),
        ("Handmade Ceramic Mug", "Home", 32.00, 1.1, (6, 6, 6), "Wheel-thrown stoneware, dishwasher safe."),
        ("Soy Candle: Live Oak", "Home", 22.00, 1.0, (5, 5, 5), "60-hour burn, cotton wick."),
        ("Texas Wildflower Field Guide", "Books", 18.00, 1.0, (9, 6, 1), "300+ species with color photos."),
        ("Prickly Pear Lip Balm Set", "Beauty", 14.00, 0.2, (4, 3, 1), "Three tubes, beeswax base."),
        ("Mesquite Cutting Board", "Home", 75.00, 4.5, (18, 12, 2), "End-grain mesquite, finished with food-safe oil."),
        ("Cast Iron Skillet 12in", "Home", 54.00, 7.9, (20, 13, 3), "Pre-seasoned, made in the USA."),
    ]),
}
CUSTOMERS = [("Alex Rivera", "customer@longhorn.market", ("2400 Nueces St", "Austin", "TX", "78705")),
             ("Sam Okafor", "sam@longhorn.market", ("350 5th Ave", "New York", "NY", "10118")),
             ("Taylor Brooks", "taylor@longhorn.market", ("1600 Pennsylvania Ave NW", "Washington", "DC", "20500"))]


def user(name, email, role, addr=("", "", "", "")):
    u = User(name=name, email=email, role=role, street=addr[0], city=addr[1], state=addr[2], zip=addr[3],
             created_at=now() - timedelta(days=random.randint(20, 90)))
    u.set_password("password123")
    db.session.add(u)
    return u


def seed():
    if User.query.filter_by(email="admin@longhorn.market").first():
        return "Already seeded. Delete instance/market.db to start over."
    random.seed(78705)
    user("Avery Admin", "admin@longhorn.market", "admin")
    products = []
    for (name, email), (store_name, tagline, items) in STORES.items():
        s = Store(owner=user(name, email, "seller"), name=store_name, tagline=tagline,
                  slug=store_name.lower().replace(" ", "-").replace("&", "and").replace(".", ""),
                  description=f"{store_name} is an independent Austin seller. {tagline}.")
        db.session.add(s)
        for pname, cat, price, wt, (l, w, h), desc in items:
            p = Product(store=s, name=pname, category=cat, price_cents=int(price * 100), weight_lb=wt,
                        length_in=l, width_in=w, height_in=h, description=desc, stock=random.choice([0, 3, 12, 25, 40]),
                        created_at=now() - timedelta(days=random.randint(1, 60)))
            db.session.add(p)
            products.append(p)
    customers = [user(n, e, "customer", a) for n, e, a in CUSTOMERS]
    db.session.flush()

    # 30 days of order history so the dashboards have something to show.
    for n in range(45):
        c = random.choice(customers)
        picks = random.sample(products, random.randint(1, 3))
        placed = now() - timedelta(days=random.randint(0, 29), hours=random.randint(0, 23))
        age = (now() - placed).days
        o = Order(user=c, created_at=placed, shipping_service="UPS Ground", shipping_cents=random.choice([0, 1189, 1432]),
                  ship_name=c.name, ship_street=c.street, ship_city=c.city, ship_state=c.state, ship_zip=c.zip,
                  subtotal_cents=0, tax_cents=0, total_cents=0)
        for p in picks:
            status = ("delivered" if age > 7 else "shipped" if age > 2 else "pending")
            status = random.choices([status, "cancelled", "return_requested", "returned"], [85, 6, 5, 4])[0]
            if status in ("return_requested", "returned") and age <= 7:
                status = "delivered" if age > 2 else "pending"
            o.items.append(OrderItem(product=p, store=p.store, name=p.name, unit_price_cents=p.price_cents,
                                     qty=random.randint(1, 2), status=status, updated_at=placed + timedelta(days=3),
                                     tracking="" if status in ("pending", "cancelled") else f"1Z{random.randrange(16**16):016X}",
                                     return_reason="Arrived with a cracked lid." if "return" in status else ""))
        o.subtotal_cents = sum(i.line_cents for i in o.items)
        o.tax_cents = round(o.subtotal_cents * 0.0825)
        o.total_cents = o.subtotal_cents + o.tax_cents + o.shipping_cents
        db.session.add(o)

    conv = Conversation(customer=customers[0], store=products[0].store, product=products[0],
                        subject=f"Question about {products[0].name}")
    conv.messages += [Message(sender=customers[0], body="Does the daypack fit a 16 inch laptop?"),
                      Message(sender=products[0].store.owner, body="It does! The sleeve fits up to 16.2 in.")]
    db.session.add(conv)
    db.session.commit()
    return f"Seeded {len(products)} products, 3 stores, 45 orders. Sign in as admin@longhorn.market / password123."
