from django.db import models

class Conversation(models.Model):
    customer = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="customer_conversations")
    seller = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="seller_conversations")
    product = models.ForeignKey("catalog.Product", on_delete=models.SET_NULL, null=True, blank=True)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
