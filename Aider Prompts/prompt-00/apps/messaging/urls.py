from rest_framework.routers import DefaultRouter
from .views import ThreadViewSet

router = DefaultRouter()
router.register(r'threads', ThreadViewSet, basename='thread')

urlpatterns = router.urls
