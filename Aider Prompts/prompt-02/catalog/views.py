from rest_framework import viewsets, mixins, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from accounts.permissions import IsSeller, IsAdmin
from .models import Category, Product, ProductImage
from .serializers import CategorySerializer, ProductSerializer, ProductImageSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title','description']
    filterset_fields = ['category','store','is_active']
    def get_queryset(self):
        qs = Product.objects.select_related('store','category').filter(is_active=True)
        u = self.request.user
        if u.is_authenticated and u.role == 'seller':
            return Product.objects.filter(store__owner=u)
        if u.is_authenticated and u.role == 'admin':
            return Product.objects.all()
        return qs
    def perform_create(self, serializer):
        serializer.save(store=self.request.user.store)

class ProductImageViewSet(viewsets.ModelViewSet):
    serializer_class = ProductImageSerializer
    def get_queryset(self):
        u = self.request.user
        if u.role == 'seller':
            return ProductImage.objects.filter(product__store__owner=u)
        if u.role == 'admin':
            return ProductImage.objects.all()
        return ProductImage.objects.none()
