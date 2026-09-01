from rest_framework import serializers


class ShippingItemSerializer(serializers.Serializer):
    weight_lb = serializers.FloatField()
    length_in = serializers.FloatField()
    width_in = serializers.FloatField()
    height_in = serializers.FloatField()
    qty = serializers.IntegerField(min_value=1, default=1)


class ShippingRateRequestSerializer(serializers.Serializer):
    destination_postal_code = serializers.CharField()
    items = ShippingItemSerializer(many=True)


class ShippingRateSerializer(serializers.Serializer):
    service = serializers.CharField()
    code = serializers.CharField()
    cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    estimate = serializers.BooleanField(default=True)
