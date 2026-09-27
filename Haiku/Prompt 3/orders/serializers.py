from rest_framework import serializers
from .models import Order, OrderItem, ReturnRequest, CancellationRequest, ShippingRate
from core.serializers import ProductSerializer, StoreSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    store = StoreSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'store', 'quantity', 'price_at_purchase')
        read_only_fields = ('id',)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'status', 'total_price', 'shipping_price', 'tax',
            'shipping_address', 'shipping_city', 'shipping_state', 'shipping_zip', 'shipping_country',
            'billing_address', 'billing_city', 'billing_state', 'billing_zip', 'billing_country',
            'tracking_number', 'estimated_delivery', 'payment_method', 'payment_status',
            'items', 'created_at'
        )
        read_only_fields = ('id', 'order_number', 'created_at', 'payment_status', 'stripe_payment_id')


class ReturnRequestSerializer(serializers.ModelSerializer):
    order_item = OrderItemSerializer(read_only=True)

    class Meta:
        model = ReturnRequest
        fields = ('id', 'order', 'order_item', 'reason', 'description', 'status', 'return_tracking', 'refund_amount', 'admin_notes', 'created_at')
        read_only_fields = ('id', 'created_at', 'status', 'refund_amount', 'admin_notes', 'return_tracking')


class CancellationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationRequest
        fields = ('id', 'order', 'reason', 'status', 'refund_amount', 'admin_notes', 'created_at')
        read_only_fields = ('id', 'created_at', 'status', 'refund_amount', 'admin_notes')


class ShippingRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingRate
        fields = ('id', 'carrier', 'service_type', 'base_rate', 'per_pound', 'per_mile', 'is_active')
        read_only_fields = ('id',)
