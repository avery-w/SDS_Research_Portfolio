"""Views for the catalog app."""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsSeller
from stores.models import Store

from .models import Category, Inventory, InventoryLog, Product
from .serializers import (
    CategorySerializer,
    InventoryLogSerializer,
    InventorySerializer,
    ProductImageSerializer,
    ProductSerializer,
)


class CategoryListView(generics.ListCreateAPIView):
    """List categories (public) or create one (admin)."""

    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        qs = Category.objects.filter(is_active=True)
        parent = self.request.query_params.get("parent")
        if parent is not None:
            if parent == "none":
                qs = qs.filter(parent__isnull=True)
            else:
                qs = qs.filter(parent_id=parent)
        return qs


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a category (admin only writes)."""

    serializer_class = CategorySerializer
    queryset = Category.objects.all()

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return [permissions.AllowAny()]


class ProductListView(generics.ListCreateAPIView):
    """List/search products (public) or create one (seller)."""

    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsSeller()]
        return super().get_permissions()

    def get_queryset(self):
        qs = Product.objects.select_related("store", "category").prefetch_related(
            "images", "inventory"
        )
        # Public listing only shows active products from active stores.
        if not self.request.user.is_authenticated or not (
            self.request.user.is_seller or self.request.user.is_admin_role
        ):
            qs = qs.filter(is_active=True, store__is_active=True)

        search = self.request.query_params.get("search")
        category = self.request.query_params.get("category")
        store = self.request.query_params.get("store")
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        min_rating = self.request.query_params.get("min_stock")

        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(sku__icontains=search)
            )
        if category:
            qs = qs.filter(category__slug=category)
        if store:
            qs = qs.filter(store__slug=store)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        return qs

    def perform_create(self, serializer):
        store = Store.objects.get(owner=self.request.user)
        serializer.save(store=store)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve a product, or update/delete if you're the seller or admin."""

    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("store").prefetch_related(
        "images", "inventory"
    )

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method in ("PUT", "PATCH", "DELETE"):
            user = request.user
            if not (user.is_admin_role or obj.store.owner_id == user.id):
                self.permission_denied(request)


class MyProductsView(generics.ListAPIView):
    """List the current seller's own products."""

    serializer_class = ProductSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        store = Store.objects.get(owner=self.request.user)
        return Product.objects.filter(store=store).prefetch_related("images")


class AdminProductListView(generics.ListAPIView):
    """Admin: list all products including inactive ones."""

    serializer_class = ProductSerializer
    permission_classes = [IsAdmin]
    queryset = Product.objects.select_related("store")

    def get_queryset(self):
        qs = super().get_queryset()
        active = self.request.query_params.get("active")
        if active is not None:
            qs = qs.filter(is_active=active.lower() == "true")
        return qs


class ProductInventoryView(APIView):
    """Read/update the inventory for the seller's product."""

    permission_classes = [IsSeller]

    def get_object(self, product_id):
        product = get_object_or_404(Product, pk=product_id)
        user = self.request.user
        if not (user.is_admin_role or product.store.owner_id == user.id):
            self.permission_denied(self.request)
        inventory, _ = Inventory.objects.get_or_create(
            product=product, defaults={"quantity": product.stock_quantity}
        )
        return product, inventory

    def get(self, request, product_id):
        product, inventory = self.get_object(product_id)
        return Response(InventorySerializer(inventory).data)

    def post(self, request, product_id):
        product, inventory = self.get_object(product_id)
        serializer = InventorySerializer(
            inventory, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        old_quantity = inventory.quantity
        inventory = serializer.save()
        # Sync the product's stock_quantity field.
        product.stock_quantity = inventory.quantity
        product.save(update_fields=["stock_quantity"])
        InventoryLog.objects.create(
            inventory=inventory,
            quantity_change=inventory.quantity - old_quantity,
            reason=request.data.get("reason", "Manual adjustment"),
            created_by=request.user,
        )
        return Response(InventorySerializer(inventory).data)


class ProductImageView(APIView):
    """Add or manage images for the seller's product."""

    permission_classes = [IsSeller]

    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        user = request.user
        if not (user.is_admin_role or product.store.owner_id == user.id):
            self.permission_denied(request)
        serializer = ProductImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
