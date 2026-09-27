from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from shop import views

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("accounts/login/", views.RateLimitedLoginView.as_view(), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/signup/", views.signup, name="signup"),
    path("accounts/profile/", views.account, name="account"),
    path("", views.home, name="home"),
    path("stores/<int:pk>/", views.store_detail, name="store_detail"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart, name="cart"),
    path("cart/<int:pk>/", views.cart_set, name="cart_set"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.orders, name="orders"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/<int:pk>/return/", views.order_return, name="order_return"),
    path("seller/", views.seller_dashboard, name="seller_dashboard"),
    path("seller/products/new/", views.product_edit, name="product_new"),
    path("seller/products/<int:pk>/", views.product_edit, name="product_edit"),
    path("seller/images/<int:pk>/delete/", views.image_delete, name="image_delete"),
    path("seller/orders/<int:pk>/", views.seller_order, name="seller_order"),
    path("messages/", views.inbox, name="inbox"),
    path("messages/<int:user_id>/", views.thread, name="thread"),
    path("staff/analytics/", views.analytics, name="analytics"),
    path("api/shipping/rates/", views.api_shipping_rates, name="api_shipping_rates"),
    path("api/chat/", views.api_chat, name="api_chat"),
]

if settings.DEBUG:  # in production Caddy serves /media
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
