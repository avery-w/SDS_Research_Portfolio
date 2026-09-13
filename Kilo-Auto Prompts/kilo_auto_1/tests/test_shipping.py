"""Tests for shipping calculator."""
from __future__ import annotations

import pytest

from app.shipping import calculate_ups_rates


class TestCalculateUPSRates:
    def test_returns_four_services(self):
        result = calculate_ups_rates(2.5, "10001")
        assert len(result.rates) == 4
        services = {r.service for r in result.rates}
        assert services == {"ups_ground", "ups_3day", "ups_2day", "ups_next_day"}

    def test_ground_is_cheapest(self):
        result = calculate_ups_rates(2.5, "10001")
        rates = {r.service: r.rate for r in result.rates}
        assert rates["ups_ground"] < rates["ups_3day"]
        assert rates["ups_ground"] < rates["ups_2day"]
        assert rates["ups_ground"] < rates["ups_next_day"]

    def test_zone_lookup_local(self):
        """Austin local ZIP should map to zone 2."""
        result = calculate_ups_rates(1.0, "78701")
        assert result.package["zone"] == 2

    def test_zone_lookup_northeast(self):
        """NY ZIP should map to zone 3 or higher."""
        result = calculate_ups_rates(1.0, "10001")
        assert result.package["zone"] >= 3

    def test_zone_lookup_west_coast(self):
        """CA ZIP should map to zone 8."""
        result = calculate_ups_rates(1.0, "90001")
        assert result.package["zone"] == 8

    def test_dimensional_weight(self):
        result = calculate_ups_rates(1.0, "10001", length=20, width=15, height=10)
        assert result.package["dim_weight_lbs"] is not None
        assert result.package["billable_weight_lbs"] >= 1.0

    def test_residential_surcharge(self):
        result_res = calculate_ups_rates(1.0, "10001", is_residential=True)
        res_ground = [r for r in result_res.rates if r.service == "ups_ground"][0]
        result_com = calculate_ups_rates(1.0, "10001", is_residential=False)
        com_ground = [r for r in result_com.rates if r.service == "ups_ground"][0]
        assert res_ground.rate >= com_ground.rate

    def test_fuel_surcharge_not_in_basic_rate(self):
        """Rates should be base published rates; fuel surcharge applied separately."""
        result = calculate_ups_rates(5.0, "10001")
        for r in result.rates:
            assert r.rate > 0

    def test_origin_format(self):
        result = calculate_ups_rates(1.0, "10001")
        assert "110 Inner Campus Drive" in result.origin
        assert "Austin" in result.origin
        assert "78705" in result.origin

    def test_minimum_weight(self):
        result = calculate_ups_rates(0.1, "10001")
        assert result.package["billable_weight_lbs"] >= 1.0

    def test_heavy_package(self):
        result = calculate_ups_rates(50.0, "10001")
        assert result.rates[0].rate > 5  # should be expensive for 50 lbs

    def test_returns_estimated_days(self):
        result = calculate_ups_rates(1.0, "10001")
        days = {r.service: r.estimated_business_days for r in result.rates}
        assert days["ups_next_day"] == 1
        assert days["ups_2day"] == 2
        assert days["ups_3day"] == 3
        assert days["ups_ground"] == 5

    def test_filter_services(self):
        result = calculate_ups_rates(1.0, "10001", services=["ups_ground"])
        assert len(result.rates) == 1
        assert result.rates[0].service == "ups_ground"

    def test_invalid_zip_default(self):
        result = calculate_ups_rates(1.0, "00000")
        assert len(result.rates) == 4
