from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from catalog.models import Product
from orders.models import Order
from .services import chatbot_reply

class ChatView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        q = (request.data.get('q') or '')[:2000]
        product_id = request.data.get('product_id')
        order_id = request.data.get('order_id')
        ctx = ''
        if product_id:
            try:
                p = Product.objects.get(id=product_id, is_active=True)
                ctx = f"Product: {p.title}, Price: {p.price_cents/100:.2f} USD, Store: {p.store.name}, Description: {p.description[:500]}"
            except Product.DoesNotExist:
                ctx = "Product not found."
        if order_id and request.user.is_authenticated:
            try:
                o = Order.objects.get(id=order_id, customer=request.user)
                ctx += f"\nOrder status: {o.status}, placed: {o.created_at.date()}, total: {o.total_cents/100:.2f} USD."
            except Order.DoesNotExist:
                ctx += "\nOrder not found or not accessible."
        answer = chatbot_reply(q, ctx)
        return Response({'answer': answer, 'suggestion': 'Use Message Seller to ask directly if you need confirmation or custom options.'})
