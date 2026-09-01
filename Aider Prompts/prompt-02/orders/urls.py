from rest_framework.routers import DefaultRouter
from .views import CartViewSet, OrderViewSet, CancellationViewSet, ReturnViewSet
router = DefaultRouter()
router.register('cart', CartViewSet, basename='cart')
router.register('orders', OrderViewSet, basename='orders')
router.register('cancellations', CancellationViewSet, basename='cancellations')
router.register('returns', ReturnViewSet, basename='returns')
urlpatterns = router.urls
