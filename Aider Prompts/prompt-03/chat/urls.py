from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, AssistantView

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")

urlpatterns = [
    path("", include(router.urls)),
    path("assistant/", AssistantView.as_view(), name="assistant"),
]
