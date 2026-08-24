from django.urls import path
from .views import RuleBasedChatAPIView

urlpatterns = [
    path('message/', RuleBasedChatAPIView.as_view(), name='chat-message'),
]
