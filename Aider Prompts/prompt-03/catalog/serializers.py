from rest_framework import serializers
from .models import Category, Product, ProductImage, Inventory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("url", "alt", "position")

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ("quantity", "reserved", "allow_backorder")

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    inventory = InventorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("created_at",)
