from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, ProductImageViewSet
router = DefaultRouter()
router.register('categories', CategoryViewSet)
router.register('products', ProductViewSet, basename='product')
router.register('images', ProductImageViewSet, basename='product-image')
urlpatterns = router.urls
