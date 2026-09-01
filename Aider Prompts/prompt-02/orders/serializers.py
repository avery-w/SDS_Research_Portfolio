import bleach
from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, CancellationRequest, ReturnRequest
from catalog.models import Product

class CartItemSerializer(serializers.ModelSerializer):
    class Meta: model = CartItem; fields = ('id','product','quantity')

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    class Meta: model = Cart; fields = ('user','items')

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta: model = OrderItem; fields = ('product','title_snapshot','price_cents','quantity')

class AddressSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    line1 = serializers.CharField(max_length=200)
    line2 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120)
    state = serializers.CharField(max_length=2)
    zip = serializers.CharField(max_length=10)
    country = serializers.CharField(max_length=2)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer()
    billing_address = AddressSerializer(required=False)
    class Meta:
        model = Order
        fields = ('id','customer','store','status','subtotal_cents','shipping_cents','tax_cents','total_cents','shipping_address','billing_address','items','created_at')
        read_only_fields = ('id','customer','status','subtotal_cents','shipping_cents','tax_cents','total_cents','created_at')

class CancellationRequestSerializer(serializers.ModelSerializer):
    class Meta: model = CancellationRequest; fields = ('id','order','reason','status','created_at'); read_only_fields=('status','created_at')
    def validate_reason(self, v): return bleach.clean(v, strip=True)

class ReturnRequestSerializer(serializers.ModelSerializer):
    class Meta: model = ReturnRequest; fields = ('id','order','reason','status','rma_number','created_at'); read_only_fields=('status','rma_number','created_at')
    def validate_reason(self, v): return bleach.clean(v, strip=True)
