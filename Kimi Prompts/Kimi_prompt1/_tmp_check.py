"""Temporary smoke check: models, schema and the UPS rating engine."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from flask import Flask  # noqa: E402

from marketplace import models  # noqa: E402,F401
from marketplace.extensions import db  # noqa: E402
from marketplace.services import ups  # noqa: E402

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    print(f"tables={len(db.metadata.tables)}")

# --- rating ---------------------------------------------------------------
ORIGIN = ups.ShippingAddress(
    name="Mercado Fulfillment Hub",
    street1="110 Inner Campus Drive",
    city="Austin",
    state="TX",
    postal_code="78705",
    residential=False,
)

dest = ups.ShippingAddress(
    name="Ada Lovelace",
    street1="1 Infinite Loop",
    city="Cupertino",
    state="CA",
    postal_code="95014",
    residential=True,
)

print("zone 78705 -> 95014 =", ups.zone_for("78705", "95014"))

parcels = ups.build_parcels(
    [
        ups.ShippableUnit("Coffee Grinder", 10, 8, 6, 80, declared_value_cents=8999),
        ups.ShippableUnit("Bean Sampler", 8, 6, 4, 32, declared_value_cents=2499),
    ]
)
print("parcels:", [p.to_dict() for p in parcels])

quotes = ups.rate_shipment(ORIGIN, dest, parcels)
for q in quotes:
    print(
        f"{q.service_name:<22} zone={q.zone} days={q.transit_days} "
        f"billable={q.billable_weight_lb}lb total={q.total_display} "
        f"arrives={q.arrival_display}"
    )

ground = ups.find_quote(quotes, ups.ShippingService.GROUND)
print("ground lines:", [line.to_dict() for line in ground.charge_lines])

# multi-parcel: 4 x 20 lb units must split
many = ups.build_parcels(
    [ups.ShippableUnit("Free Weights", 14, 10, 8, 320) for _ in range(4)]
)
print("split parcels:", len(many), [round(p.billable_weight_lb, 1) for p in many])

# errors
for bad in [
    ups.ShippingAddress(name="X", street1="1 A St", city="Austin", state="TX", postal_code="787"),
    ups.ShippingAddress(name="X", street1="1 A St", city="Sydney", state="NSW", postal_code="2000", country="AU"),
]:
    try:
        ups.rate_shipment(ORIGIN, bad, parcels)
    except ups.RateError as exc:
        print("RateError:", exc.code, "-", exc.message)

try:
    ups.rate_shipment(
        ORIGIN, dest, parcels, service_codes=[ups.ShippingService.STANDARD]
    )
except ups.RateError as exc:
    print("RateError:", exc.code, "-", exc.message)

# non-contiguous excludes ground
quotes_hi = ups.rate_shipment(
    ORIGIN,
    ups.ShippingAddress(
        name="A", street1="1 A St", city="Honolulu", state="HI", postal_code="96813"
    ),
    parcels,
)
print("HI services:", [q.service_code for q in quotes_hi])
print("cheapest:", ups.cheapest_quote(quotes).service_name)
print("fastest:", ups.fastest_quote(quotes).service_name)
print("OK")
