import requests
from app.config import get_settings

settings = get_settings()

def calculate_shipping_rate(destination_zip: str, weight_oz: float) -> dict:
    """
    Calculate shipping rate using UPS API guidelines.
    For demo, returns realistic rates based on weight and distance.
    Production: integrate with actual UPS API.
    ponytail: mocked rates until real UPS account integration
    """

    base_rate = 5.99
    weight_lbs = weight_oz / 16

    if weight_lbs <= 1:
        weight_charge = 0
    elif weight_lbs <= 5:
        weight_charge = weight_lbs * 0.25
    elif weight_lbs <= 20:
        weight_charge = 1.25 + (weight_lbs - 5) * 0.15
    else:
        weight_charge = 4.5 + (weight_lbs - 20) * 0.10

    distance_factor = get_distance_factor(destination_zip)
    total_rate = (base_rate + weight_charge) * distance_factor

    return {
        "rate": round(total_rate, 2),
        "carrier": "UPS Ground",
        "estimated_days": 5
    }

def get_distance_factor(destination_zip: str) -> float:
    """
    Simple distance factor based on zip code.
    Warehouse at: 110 Inner Campus Drive, Austin, TX 78705 (78705 zip)
    """
    warehouse_zip = "78705"

    if destination_zip == warehouse_zip:
        return 1.0

    try:
        warehouse_prefix = int(warehouse_zip[:3])
        dest_prefix = int(destination_zip[:3])
        distance = abs(warehouse_prefix - dest_prefix)

        if distance <= 50:
            return 1.0
        elif distance <= 200:
            return 1.15
        elif distance <= 400:
            return 1.35
        else:
            return 1.5
    except:
        return 1.35
