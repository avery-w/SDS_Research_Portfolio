from rest_framework import serializers
from .models import Product, ProductImage, Inventory


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text')


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ('quantity',)


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    inventory = InventorySerializer(read_only=True)
    store_id = serializers.IntegerField(source='store.id', read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'store_id', 'name', 'slug', 'description', 'price', 'currency', 'sku',
            'weight_lb', 'length_in', 'width_in', 'height_in', 'is_active', 'images', 'inventory'
        )


class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            'store', 'name', 'slug', 'description', 'price', 'currency', 'sku',
            'weight_lb', 'length_in', 'width_in', 'height_in', 'is_active'
        )


class ProductImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('product', 'image', 'alt_text')
