import math

ORIGIN = {
    'address1': '110 Inner Campus Drive',
    'city': 'Austin',
    'state': 'TX',
    'postal_code': '78705',
    'country': 'US'
}


def _haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


ZIP_LATLON = {
    '78705': (30.2861, -97.7394),
}


def _zip_to_latlon(zip_code):
    return ZIP_LATLON.get(zip_code, (30.2861, -97.7394))


def _billable_weight_lb(actual_lb, length_in, width_in, height_in):
    dim_weight = (length_in * width_in * height_in) / 139.0
    return max(float(actual_lb), float(dim_weight))


def estimate_ups_rates(dest_postal_code, items):
    """
    items: list of dicts [{'weight_lb': float, 'length_in': float, 'width_in': float, 'height_in': float, 'qty': int}]
    Returns list of rate options with service codes and prices (estimates, not official).
    """
    ox, oy = _zip_to_latlon(ORIGIN['postal_code'])
    dx, dy = _zip_to_latlon(dest_postal_code)
    distance = _haversine_miles(ox, oy, dx, dy)
    if distance <= 150:
        zone_mult = 1.0
    elif distance <= 600:
        zone_mult = 1.15
    elif distance <= 1200:
        zone_mult = 1.3
    else:
        zone_mult = 1.5
    total_billable = 0.0
    for it in items:
        bw = _billable_weight_lb(it['weight_lb'], it['length_in'], it['width_in'], it['height_in'])
        total_billable += bw * max(1, int(it.get('qty', 1)))
    base = 6.50 + 0.75 * total_billable
    ground = round(base * zone_mult, 2)
    two_day = round(ground * 1.5 + 3.0, 2)
    next_day = round(ground * 2.2 + 6.0, 2)
    return [
        {'service': 'UPS Ground', 'code': '03', 'cost': ground, 'currency': 'USD', 'estimate': True},
        {'service': 'UPS 2nd Day Air', 'code': '02', 'cost': two_day, 'currency': 'USD', 'estimate': True},
        {'service': 'UPS Next Day Air', 'code': '01', 'cost': next_day, 'currency': 'USD', 'estimate': True},
    ]
