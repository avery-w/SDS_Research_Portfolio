from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from .services import get_or_create_cart, add_item, update_item, remove_item

class CartView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        session_id = request.headers.get("X-Session-Id", "")
        cart = get_or_create_cart(user=request.user if request.user.is_authenticated else None, session_id=session_id)
        return Response(CartSerializer(cart).data)

    def post(self, request):
        session_id = request.headers.get("X-Session-Id", "")
        cart = get_or_create_cart(user=request.user if request.user.is_authenticated else None, session_id=session_id)
        product_id = request.data.get("product")
        quantity = int(request.data.get("quantity", 1))
        from catalog.models import Product
        product = get_object_or_404(Product, id=product_id, is_active=True)
        try:
            item = add_item(cart, product, quantity)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)

class CartItemDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request, item_id: int):
        session_id = request.headers.get("X-Session-Id", "")
        cart = get_or_create_cart(user=request.user if request.user.is_authenticated else None, session_id=session_id)
        qty = int(request.data.get("quantity", 1))
        try:
            item = update_item(cart, item_id, qty)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CartItemSerializer(item).data)

    def delete(self, request, item_id: int):
        session_id = request.headers.get("X-Session-Id", "")
        cart = get_or_create_cart(user=request.user if request.user.is_authenticated else None, session_id=session_id)
        remove_item(cart, item_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
