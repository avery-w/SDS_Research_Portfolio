from rest_framework import serializers
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "sender", "body", "created_at")
        read_only_fields = ("id", "created_at", "sender")

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "customer", "seller", "product", "is_open", "created_at", "messages")
        read_only_fields = ("created_at",)
