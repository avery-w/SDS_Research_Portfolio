"""Lightweight health/API-root endpoints mounted at /api/."""
from django.http import JsonResponse
from django.urls import path


def api_root(request):
    """Return a simple API index with the available top-level resources."""
    return JsonResponse(
        {
            "service": "SDS Research Portfolio Marketplace API",
            "version": "1.0.0",
            "docs": "/api/",
            "resources": {
                "auth": "/api/auth/",
                "stores": "/api/stores/",
                "catalog": "/api/catalog/",
                "cart": "/api/cart/",
                "orders": "/api/orders/",
                "shipping": "/api/shipping/",
                "messages": "/api/messages/",
                "chatbot": "/api/chatbot/",
                "analytics": "/api/analytics/",
            },
        }
    )


def health(request):
    """Simple liveness check."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", api_root, name="api-root"),
    path("health/", health, name="health"),
]
