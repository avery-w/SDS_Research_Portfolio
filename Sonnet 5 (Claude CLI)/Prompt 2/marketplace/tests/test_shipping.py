"""Minimal self-check for the shipping calculator. Run: python -m pytest tests/ or python tests/test_shipping.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shipping import calculate_shipping, estimate_zone


def test_same_zip_is_zone_2():
    assert estimate_zone("78705") == 2


def test_far_zip_is_higher_zone():
    assert estimate_zone("98101") > estimate_zone("78704")  # Seattle vs next-door Austin


def test_invalid_zip_raises():
    try:
        estimate_zone("abc")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_heavier_costs_more():
    light_cost, _ = calculate_shipping(1, "78704", "ground")
    heavy_cost, _ = calculate_shipping(20, "78704", "ground")
    assert heavy_cost > light_cost


def test_faster_service_costs_more():
    ground_cost, _ = calculate_shipping(5, "10001", "ground")
    next_day_cost, _ = calculate_shipping(5, "10001", "next_day")
    assert next_day_cost > ground_cost


def test_unknown_service_raises():
    try:
        calculate_shipping(5, "78704", "teleport")
        assert False, "expected ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok: {name}")
    print("all shipping tests passed")
