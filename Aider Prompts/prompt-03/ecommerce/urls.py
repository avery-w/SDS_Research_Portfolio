from django.contrib import admin
from django.urls import path, include
from . import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/stores/", include("stores.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/cart/", include("cart.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/shipping/", include("shipping.urls")),
    path("api/chat/", include("chat.urls")),
    path("healthz", health.healthz),
]

try:
    urlpatterns += [path("", include("django_prometheus.urls"))]
except Exception:
    pass
