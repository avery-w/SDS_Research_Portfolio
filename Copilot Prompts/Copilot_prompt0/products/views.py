from rest_framework import viewsets
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer

    def perform_create(self, serializer):
        # If the request user is a seller, associate them automatically
        user = getattr(self.request, 'user', None)
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            serializer.save(seller=user)
        else:
            serializer.save()
