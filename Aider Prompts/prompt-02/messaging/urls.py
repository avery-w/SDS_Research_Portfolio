from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageViewSet
router = DefaultRouter()
router.register('conversations', ConversationViewSet, basename='conversations')
router.register('messages', MessageViewSet, basename='messages')
urlpatterns = router.urls
