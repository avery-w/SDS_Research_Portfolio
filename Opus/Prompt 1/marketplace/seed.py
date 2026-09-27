from .models import Product, Store, User, db

DEMO_PASSWORD = "password123"


def seed_demo():
    if db.session.query(User).filter_by(email="admin@example.com").first():
        return
    users = {}
    for role in ("admin", "seller", "customer"):
        users[role] = User(email=f"{role}@example.com", name=f"Demo {role.title()}", role=role)
        users[role].set_password(DEMO_PASSWORD)
    users["customer"].street, users["customer"].city = "350 5th Ave", "New York"
    users["customer"].state, users["customer"].zip = "NY", "10118"
    db.session.add_all(users.values())
    store = Store(owner=users["seller"], name="Forty Acres Goods", description="Handmade goods from Austin, Texas.")
    db.session.add(store)
    for name, category, price, stock, weight, dims, desc in [
        ("Burnt Orange Hoodie", "Apparel", 4999, 25, 1.5, (14, 12, 3), "Heavyweight cotton fleece hoodie. Sizes S-XXL."),
        ("Ceramic Coffee Mug", "Home", 1899, 40, 1.2, (6, 6, 5), "Hand-thrown stoneware mug, 14 oz, dishwasher safe."),
        ("Leather Notebook", "Stationery", 3499, 15, 0.8, (9, 7, 1.5), "Refillable A5 notebook with full-grain leather cover."),
        ("Cast Iron Skillet", "Kitchen", 6499, 10, 8.0, (18, 11, 3), "Pre-seasoned 12 inch cast iron skillet."),
        ("Desk Lamp", "Home", 8999, 8, 4.5, (20, 10, 10), "Adjustable LED desk lamp with warm and cool modes."),
    ]:
        db.session.add(
            Product(
                store=store, name=name, category=category, price_cents=price, stock=stock, weight_lb=weight,
                length_in=dims[0], width_in=dims[1], height_in=dims[2], description=desc,
            )
        )
    db.session.commit()
