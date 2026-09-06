"""Root URL configuration for the marketplace project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/stores/", include("stores.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/cart/", include("carts.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/shipping/", include("shipping.urls")),
    path("api/messages/", include("messaging.urls")),
    path("api/chatbot/", include("chatbot.urls")),
    path("api/analytics/", include("analytics.urls")),
    path("api/", include("catalog.health_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
