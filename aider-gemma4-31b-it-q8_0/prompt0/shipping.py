import os
import requests
from fastapi import HTTPException

# Hardcoded Origin
ORIGIN_ADDRESS = {
    "street": "110 Inner Campus Drive",
    "city": "Austin",
    "state": "TX",
    "zip": "78705"
}

def calculate_ups_rate(destination_zip: str, weight: float):
    """
    Calculates shipping rate using UPS API.
    Mocks the response if API key is missing for development.
    """
    api_key = os.getenv("UPS_API_KEY")
    
    if not api_key:
        # Mock Logic: Base rate $5 + $1 per 100 miles (simulated) + $0.50 per lb
        # In a real scenario, we'd use a distance matrix API
        mock_distance_factor = 2.5 
        mock_rate = 5.0 + (mock_distance_factor * 2) + (weight * 0.5)
        return round(mock_rate, 2)

    try:
        # This is a conceptual implementation of the UPS REST API call
        url = "https://onlinetools.ups.com/api/rating/v1/rates"
        payload = {
            "origin": ORIGIN_ADDRESS,
            "destination": {"zip": destination_zip},
            "package": {"weight": weight}
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        return data["rates"][0]["amount"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shipping calculation failed: {str(e)}")
