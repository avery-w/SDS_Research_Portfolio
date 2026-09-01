from rest_framework import serializers
from .models import Address, Order, OrderItem, CancellationRequest, ReturnRequest


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'quantity', 'unit_price', 'total_price')
        read_only_fields = ('unit_price', 'total_price')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'user', 'store', 'shipping_address', 'subtotal', 'shipping_cost', 'total', 'status',
            'shipping_service', 'items', 'created_at'
        )
        read_only_fields = ('user', 'subtotal', 'shipping_cost', 'total', 'status', 'created_at')


class CheckoutItem(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class PlaceOrderSerializer(serializers.Serializer):
    address = AddressSerializer()
    shipping_choices = serializers.JSONField()  # {store_id: {'service_code': '03', 'service_name': 'UPS Ground'}}


class CancellationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationRequest
        fields = ('id', 'order', 'reason', 'approved', 'created_at')
        read_only_fields = ('approved', 'created_at')


class ReturnRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnRequest
        fields = ('id', 'order_item', 'reason', 'approved', 'created_at')
        read_only_fields = ('approved', 'created_at')
