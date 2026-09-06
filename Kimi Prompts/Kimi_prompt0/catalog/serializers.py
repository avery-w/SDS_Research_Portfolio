"""Serializers for the catalog app."""
from rest_framework import serializers

from .models import Category, Inventory, InventoryLog, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    """Serialize a product category."""

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "description",
            "is_active",
            "children",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_children(self, obj):
        children = obj.children.all()
        if children.exists():
            return CategorySerializer(children, many=True).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """Serialize a product image."""

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = [
            "id",
            "image",
            "image_url",
            "alt_text",
            "is_primary",
            "sort_order",
        ]
        read_only_fields = ["id"]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class InventorySerializer(serializers.ModelSerializer):
    """Serialize a product's inventory record."""

    available = serializers.ReadOnlyField()

    class Meta:
        model = Inventory
        fields = [
            "id",
            "product",
            "quantity",
            "reserved",
            "available",
            "low_stock_threshold",
            "updated_at",
        ]
        read_only_fields = ["id", "product", "available", "updated_at"]


class InventoryLogSerializer(serializers.ModelSerializer):
    """Serialize an inventory change log entry."""

    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True, default=""
    )

    class Meta:
        model = InventoryLog
        fields = [
            "id",
            "inventory",
            "quantity_change",
            "reason",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    """Serialize a product."""

    store_name = serializers.CharField(source="store.name", read_only=True)
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=""
    )
    images = ProductImageSerializer(many=True, read_only=True)
    main_image = serializers.ReadOnlyField()
    inventory = InventorySerializer(read_only=True)
    is_in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "store",
            "store_name",
            "category",
            "category_name",
            "name",
            "slug",
            "description",
            "sku",
            "price",
            "compare_at_price",
            "currency",
            "weight_oz",
            "length_in",
            "width_in",
            "height_in",
            "stock_quantity",
            "is_active",
            "is_featured",
            "is_in_stock",
            "main_image",
            "images",
            "inventory",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_is_in_stock(self, obj):
        return obj.stock_quantity > 0

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate(self, attrs):
        compare_at = attrs.get("compare_at_price")
        price = attrs.get("price")
        if compare_at is not None and price is not None and compare_at < price:
            raise serializers.ValidationError(
                "Compare-at price must be greater than or equal to price."
            )
        return attrs
