from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ProductImageUploadViewSet

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product')
router.register(r'images', ProductImageUploadViewSet, basename='product-image')

urlpatterns = router.urls
