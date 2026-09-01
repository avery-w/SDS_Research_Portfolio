from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Message
from .serializers import MessageSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

RULES = [
    (['return', 'refund', 'cancellation'], "To start a return or refund, go to your order history and select the order then 'Request Return'."),
    (['shipping', 'delivery', 'status'], "Shipping times vary by seller. You can message the seller directly from the product page or view tracking in order details."),
    (['price', 'discount', 'sale'], "Check the product page for current promotions; sellers may offer coupons."),
]

class RuleBasedChatAPIView(APIView):
    def post(self, request):
        payload = request.data
        user_id = payload.get('user_id')
        content = payload.get('content', '')
        to_seller_id = payload.get('to_seller_id')

        if not user_id or not content:
            return Response({'detail': 'user_id and content required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sender = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'user not found'}, status=status.HTTP_400_BAD_REQUEST)

        # Basic rule matching
        lc = content.lower()
        for keywords, reply in RULES:
            if any(k in lc for k in keywords):
                return Response({'reply': reply})

        # If user intends to message a seller, persist the message and mark as delivered=False
        if to_seller_id:
            try:
                recipient = User.objects.get(pk=to_seller_id)
            except User.DoesNotExist:
                return Response({'detail': 'seller not found'}, status=status.HTTP_400_BAD_REQUEST)

            msg = Message.objects.create(sender=sender, recipient=recipient, content=content)
            ser = MessageSerializer(msg)
            return Response({'routed_to_seller': True, 'message': ser.data})

        # Default fallback reply
        return Response({'reply': "Thanks for the message — a seller or support rep will follow up. Try including 'order' or 'return' if relevant."})
