import bleach
from rest_framework import serializers
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta: model = Message; fields = ('id','sender','body','created_at'); read_only_fields=('id','sender','created_at')
    def validate_body(self, v): return bleach.clean(v, strip=True)

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    class Meta: model = Conversation; fields = ('id','customer','store','messages','created_at'); read_only_fields=('id','created_at')
