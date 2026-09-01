from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from accounts.permissions import IsSeller, IsAdmin
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from .storage import generate_presigned_post

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["slug", "parent"]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("store").filter(is_active=True)
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["store", "slug"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "price"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsSeller()]
        if self.action in ["retrieve", "list"]:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        if IsAdmin().has_permission(self.request, self):
            return Product.objects.select_related("store").all()
        return qs

    def perform_create(self, serializer):
        # Ensure seller owns the store
        store = serializer.validated_data.get("store")
        if not store or store.owner_id != self.request.user.id:
            raise permissions.PermissionDenied("You can only add products to your own store.")
        serializer.save()

    def perform_update(self, serializer):
        store = serializer.validated_data.get("store") or serializer.instance.store
        if store.owner_id != self.request.user.id and not IsAdmin().has_permission(self.request, self):
            raise permissions.PermissionDenied("You can only modify products in your own store.")
        serializer.save()

class PresignView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def post(self, request):
        content_type = request.data.get("content_type", "")
        if not content_type.startswith("image/"):
            return Response({"detail": "Invalid content type"}, status=status.HTTP_400_BAD_REQUEST)
        data = generate_presigned_post("uploads/images", content_type, max_bytes=5 * 1024 * 1024)
        return Response(data)
