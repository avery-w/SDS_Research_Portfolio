from rest_framework import viewsets, mixins, permissions
from accounts.permissions import IsAdmin
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    def get_queryset(self):
        u = self.request.user
        if u.role == 'admin': return Conversation.objects.all()
        if u.role == 'seller': return Conversation.objects.filter(store__owner=u)
        return Conversation.objects.filter(customer=u)

    def perform_create(self, serializer):
        # customer starts conversation with a store
        serializer.save(customer=self.request.user)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    def get_queryset(self):
        u = self.request.user
        if u.role == 'admin': return Message.objects.all()
        if u.role == 'seller': return Message.objects.filter(conversation__store__owner=u)
        return Message.objects.filter(conversation__customer=u)
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
