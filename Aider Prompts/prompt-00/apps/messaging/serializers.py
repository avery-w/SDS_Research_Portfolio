from rest_framework import serializers
from .models import Thread, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('id', 'sender', 'body', 'created_at')
        read_only_fields = ('sender', 'created_at')


class ThreadSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Thread
        fields = ('id', 'customer', 'seller', 'store', 'product', 'created_at', 'messages')
        read_only_fields = ('customer', 'created_at')
