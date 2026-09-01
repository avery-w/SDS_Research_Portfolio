from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

from products.views import ProductViewSet
from users.views import UserViewSet

router = routers.DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/orders/', include('orders.urls')),
    path('api/chat/', include('chat.urls')),
]
