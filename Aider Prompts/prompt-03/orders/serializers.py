from rest_framework import serializers
from .models import Order, OrderItem, Shipment

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("product", "quantity", "unit_price", "total_price")

class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = ("carrier", "service", "tracking_number", "cost", "status")

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipments = ShipmentSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("number", "status", "subtotal", "shipping_total", "tax_total", "grand_total", "created_at")
