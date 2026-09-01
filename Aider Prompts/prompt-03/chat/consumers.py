from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from django.contrib.auth.models import AnonymousUser
from .models import Conversation, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        user = self.scope.get("user", AnonymousUser())
        allowed = await self.user_in_conversation(user, self.conversation_id)
        if not allowed:
            await self.close()
            return
        self.room_group_name = f"conv_{self.conversation_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.send(text_data=json.dumps({"error": "auth required"}))
            return
        data = json.loads(text_data or "{}")
        body = (data.get("body") or "")[:2000]
        msg = await self.create_message(user.id, self.conversation_id, body)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat.message", "message": {"id": msg["id"], "sender": msg["sender_id"], "body": msg["body"], "created_at": msg["created_at"]}},
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def user_in_conversation(self, user, conv_id):
        try:
            c = Conversation.objects.get(id=conv_id)
            return user.is_authenticated and (c.customer_id == user.id or c.seller_id == user.id)
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def create_message(self, user_id, conv_id, body):
        m = Message.objects.create(conversation_id=conv_id, sender_id=user_id, body=body)
        return {"id": m.id, "sender_id": m.sender_id, "body": m.body, "created_at": m.created_at.isoformat()}
