import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.services.shipping import _fallback_rates  # noqa: E402


def test_fallback_rates_increase_with_weight():
    light = _fallback_rates(0.5)
    heavy = _fallback_rates(20)
    assert light[0]["cost_cents"] < heavy[0]["cost_cents"]
    # cheapest option listed first
    assert light == sorted(light, key=lambda r: r["cost_cents"])


if __name__ == "__main__":
    test_fallback_rates_increase_with_weight()
    print("ok")
