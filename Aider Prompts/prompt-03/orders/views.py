from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from ratelimit.decorators import ratelimit
from .models import Order, OrderItem
from .serializers import OrderSerializer
from .services import reserve_and_create_order, cancel_order, request_return

class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        shipping = request.data.get("shipping", {})
        from cart.services import get_or_create_cart
        cart = get_or_create_cart(user=request.user)
        if not cart.items.exists():
            return Response({"detail": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)
        order = reserve_and_create_order(request.user, cart, shipping)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

class CancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, number: str):
        order = get_object_or_404(Order, number=number, user=request.user)
        order = cancel_order(request.user, order)
        return Response(OrderSerializer(order).data)

class ReturnRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        item_id = request.data.get("order_item_id")
        reason = request.data.get("reason", "")
        oi = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
        rr = request_return(request.user, oi, reason)
        return Response({"id": rr.id, "status": rr.status}, status=status.HTTP_201_CREATED)
