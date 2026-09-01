from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from ratelimit.decorators import ratelimit
from .ups_client import shop_rates
from .utils import build_packages_from_items

def normalize_ups_shop_response(data):
    rates = []
    try:
        services = data.get("RateResponse", {}).get("RatedShipment", [])
        if isinstance(services, dict):
            services = [services]
        for s in services:
            svc = s.get("Service", {})
            code = svc.get("Code")
            name = svc.get("Description", "")
            total = s.get("TotalCharges", {}).get("MonetaryValue", "0")
            rates.append({"service_code": code, "service_name": name, "estimated_days": None, "cost": total})
    except Exception:
        pass
    return rates

@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class RateQuoteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        dest = request.data.get("destination", {}) or {}
        items = request.data.get("items", []) or []
        dest = {
            "address1": str(dest.get("address1", ""))[:100],
            "city": str(dest.get("city", ""))[:60],
            "state": str(dest.get("state", ""))[:30],
            "postal": str(dest.get("postal", ""))[:20],
            "country": str(dest.get("country", "US"))[:2],
        }
        packages = build_packages_from_items(items)
        data = shop_rates(dest, packages)
        normalized = normalize_ups_shop_response(data)
        return Response({"rates": normalized})
