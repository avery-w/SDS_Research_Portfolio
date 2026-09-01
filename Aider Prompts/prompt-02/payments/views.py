from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
from .services import create_payment_intent_cents

class PaymentIntentView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, order_id):
        order = Order.objects.get(id=order_id, customer=request.user)
        return Response(create_payment_intent_cents(order.id, order.total_cents))
