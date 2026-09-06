"""Views for the carts app."""
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product

from .models import Cart, CartItem
from .serializers import CartItemSerializer, CartSerializer


class MyCartView(APIView):
    """Retrieve the current user's shopping cart (creates it if needed)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart, context={"request": request}).data)


class AddItemView(APIView):
    """Add a product to the current user's cart."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = request.data.get("quantity", 1)
        # Validate stock.
        if product.stock_quantity <= 0:
            return Response(
                {"detail": "This product is out of stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            new_quantity = item.quantity + int(quantity)
            if new_quantity > product.stock_quantity:
                new_quantity = product.stock_quantity
            item.quantity = new_quantity
            item.save()
        return Response(
            CartSerializer(cart, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UpdateItemView(APIView):
    """Update the quantity of a cart item."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        quantity = request.data.get("quantity")
        if quantity is None:
            return Response(
                {"detail": "quantity is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        quantity = int(quantity)
        if quantity <= 0:
            item.delete()
        else:
            if quantity > item.product.stock_quantity:
                quantity = item.product.stock_quantity
            item.quantity = quantity
            item.save()
        return Response(CartSerializer(cart, context={"request": request}).data)


class RemoveItemView(APIView):
    """Remove an item from the current user's cart."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        item.delete()
        return Response(CartSerializer(cart, context={"request": request}).data)


class ClearCartView(APIView):
    """Clear all items from the current user's cart."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response(CartSerializer(cart, context={"request": request}).data)
