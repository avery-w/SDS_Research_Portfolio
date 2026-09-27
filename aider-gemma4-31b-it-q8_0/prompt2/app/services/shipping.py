import requests
import os

class ShippingService:
    ORIGIN_ADDRESS = "110 Inner Campus Drive, Austin, TX 78705"
    UPS_API_URL = "https://onlinetools.ups.com/rating/v1/rates" # Example endpoint

    @staticmethod
    def calculate_shipping(destination_zip: str, weight: float) -> float:
        api_key = os.getenv("UPS_API_KEY")
        
        if not api_key:
            return ShippingService._fallback_calculation(weight)

        try:
            # This is a conceptual implementation of the UPS API call
            payload = {
                "origin": ShippingService.ORIGIN_ADDRESS,
                "destination": destination_zip,
                "weight": weight
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.post(ShippingService.UPS_API_URL, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return float(data.get("rate", 0.0))
            
            return ShippingService._fallback_calculation(weight)
        except Exception:
            return ShippingService._fallback_calculation(weight)

    @staticmethod
    def _fallback_calculation(weight: float) -> float:
        # Basic weight-based calculation: $5 base + $2 per lb
        return 5.0 + (weight * 2.0)
