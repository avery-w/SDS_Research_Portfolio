import os, math, requests
from decimal import Decimal

ORIGIN = {
    'name': os.getenv('SHIP_FROM_NAME','UT Austin Fulfillment'),
    'line1': os.getenv('SHIP_FROM_ADDRESS1','110 Inner Campus Drive'),
    'city': os.getenv('SHIP_FROM_CITY','Austin'),
    'state': os.getenv('SHIP_FROM_STATE','TX'),
    'zip': os.getenv('SHIP_FROM_ZIP','78705'),
    'country': os.getenv('SHIP_FROM_COUNTRY','US'),
}

def _cart_dimensions_weight(cart):
    total_oz = sum(i.product.weight_oz * i.quantity for i in cart.items.select_related('product'))
    # simple volume-based dimensional weight approximation
    length = max([float(i.product.length_in) for i in cart.items.all()] + [6.0])
    width  = max([float(i.product.width_in)  for i in cart.items.all()] + [6.0])
    height = sum([float(i.product.height_in) * i.quantity for i in cart.items.all()] + [6.0])
    return max(1, int(total_oz)), max(1.0, length), max(1.0, width), max(1.0, height)

def _ups_oauth_token():
    cid = os.getenv('UPS_CLIENT_ID'); cs = os.getenv('UPS_CLIENT_SECRET')
    base = os.getenv('UPS_RATE_BASE_URL','https://wwwcie.ups.com')
    if not cid or not cs: return None
    r = requests.post(f'{base}/security/v1/oauth/token', data={'grant_type':'client_credentials'}, auth=(cid, cs), timeout=10)
    r.raise_for_status()
    return r.json().get('access_token')

def _ups_rate(dest_zip, weight_lbs, dims_in):
    token = _ups_oauth_token()
    if not token: return None
    base = os.getenv('UPS_RATE_BASE_URL','https://wwwcie.ups.com')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type':'application/json'}
    payload = {
      "Shipment": {
        "Shipper": {"Address": {"PostalCode": ORIGIN['zip'], "CountryCode": ORIGIN['country'], "StateProvinceCode": ORIGIN['state']}},
        "ShipTo": {"Address": {"PostalCode": dest_zip, "CountryCode": "US"}},
        "Package": [{
          "PackagingType": {"Code":"02"},
          "Dimensions": {"UnitOfMeasurement":{"Code":"IN"}, "Length": str(int(dims_in[0])), "Width": str(int(dims_in[1])), "Height": str(int(dims_in[2]))},
          "PackageWeight": {"UnitOfMeasurement":{"Code":"LBS"}, "Weight": str(max(1, int(weight_lbs)))}
        }]
      }
    }
    # Note: UPS Rate REST resource path can vary by version; expose via env if needed:
    url = os.getenv('UPS_RATE_PATH', f'{base}/api/rating/v2205/Shop')
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    if r.status_code >= 400: return None
    data = r.json()
    # parse to normalized list:
    options = []
    for s in (data.get('RateResponse', {}).get('RatedShipment', []) or data.get('Rate', [])):
        svc = s.get('Service', {}).get('Description') or s.get('serviceName')
        amt = s.get('TotalCharges', {}).get('MonetaryValue') or s.get('totalCharges')
        if svc and amt:
            options.append({'service': svc, 'amount_cents': int(Decimal(str(amt)) * 100)})
    return options or None

def _fallback_flat_rates(zip_code, weight_lbs):
    zone = 2 if zip_code.startswith('78') else 5  # crude: TX local cheaper
    base = 799 if zone == 2 else 1299
    per_lb = 80 if zone == 2 else 120
    return [{'service':'UPS Ground (est.)','amount_cents': base + per_lb * max(0, weight_lbs - 1)}]

def quote_shipping_for_cart(cart, destination):
    dest_zip = (destination or {}).get('zip', '')
    total_oz, L, W, H = _cart_dimensions_weight(cart)
    weight_lbs = max(1, math.ceil(total_oz / 16))
    ups = _ups_rate(dest_zip, weight_lbs, (L, W, H))
    return {'origin': ORIGIN, 'destination_zip': dest_zip, 'options': ups or _fallback_flat_rates(dest_zip, weight_lbs)}
