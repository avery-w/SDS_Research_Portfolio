import bleach
from rest_framework import serializers
from .models import Category, Product, ProductImage, Inventory
from .validators import validate_image_file

class CategorySerializer(serializers.ModelSerializer):
    class Meta: model = Category; fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta: model = ProductImage; fields = ('id','image','alt_text')
    def validate_image(self, v): validate_image_file(v); return v

class InventorySerializer(serializers.ModelSerializer):
    class Meta: model = Inventory; fields = ('sku','quantity','low_stock_threshold')

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    inventory = InventorySerializer(required=False)
    class Meta:
        model = Product
        fields = ('id','store','title','slug','description','category','price_cents','weight_oz','length_in','width_in','height_in','is_active','images','inventory','created_at')
        read_only_fields = ('id','store','created_at')
    def validate_title(self, v): return bleach.clean(v, strip=True)
    def validate_description(self, v): return bleach.clean(v or '', strip=True)
    def create(self, data):
        inv_data = data.pop('inventory', None)
        product = super().create(data)
        if inv_data: Inventory.objects.create(product=product, **inv_data)
        return product
    def update(self, instance, data):
        inv_data = data.pop('inventory', None)
        inst = super().update(instance, data)
        if inv_data:
            Inventory.objects.update_or_create(product=inst, defaults=inv_data)
        return inst
