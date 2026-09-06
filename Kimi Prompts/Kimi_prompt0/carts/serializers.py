"""Serializers for the carts app."""
from rest_framework import serializers

from catalog.models import Product
from catalog.serializers import ProductSerializer

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """Serialize a cart line item."""

    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.filter(is_active=True),
        write_only=True,
    )
    line_total = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_id",
            "quantity",
            "line_total",
            "added_at",
        ]
        read_only_fields = ["id", "product", "line_total", "added_at"]


class CartSerializer(serializers.ModelSerializer):
    """Serialize a user's cart."""

    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.ReadOnlyField()
    total_items = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ["id", "user", "items", "subtotal", "total_items", "updated_at"]
        read_only_fields = ["id", "user", "subtotal", "total_items", "updated_at"]
