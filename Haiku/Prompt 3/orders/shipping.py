import math
from decimal import Decimal
from .models import ShippingRate
from django.conf import settings

class ShippingCalculator:
    ORIGIN = settings.SHIPPING_ORIGIN

    def calculate_rate(self, destination_zip, weight_kg, dimensions=None):
        zones = self._get_ups_zone(self.ORIGIN['zip'], destination_zip)
        rates = ShippingRate.objects.filter(is_active=True).order_by('base_rate')

        if not rates.exists():
            return Decimal('0.00')

        results = []
        for rate in rates:
            cost = self._calculate_zone_cost(rate, weight_kg, zones)
            results.append({
                'carrier': rate.carrier,
                'service': rate.service_type,
                'cost': cost,
                'rate_id': rate.id,
            })

        return sorted(results, key=lambda x: x['cost'])

    def _calculate_zone_cost(self, rate, weight_kg, zone):
        base = Decimal(str(rate.base_rate))
        per_lb_cost = Decimal(str(weight_kg * 2.20462)) * Decimal(str(rate.per_pound))
        zone_multiplier = Decimal(str(1 + (zone * 0.05)))

        total = (base + per_lb_cost) * zone_multiplier
        return total

    def _get_ups_zone(self, origin_zip, dest_zip):
        try:
            origin_prefix = int(origin_zip[:3])
            dest_prefix = int(dest_zip[:3])
            zone_diff = abs(dest_prefix - origin_prefix) // 100
            return min(zone_diff, 8)
        except (ValueError, IndexError):
            return 3

    def estimate_delivery(self, service_type):
        delivery_times = {
            'Ground': 3,
            'Standard': 5,
            '2-Day': 2,
            'Overnight': 1,
        }
        return delivery_times.get(service_type, 5)
