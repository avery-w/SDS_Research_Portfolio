from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'seller', 'name', 'description', 'price', 'inventory', 'image', 'created_at']
        read_only_fields = ['created_at']
