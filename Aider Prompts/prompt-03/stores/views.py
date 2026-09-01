from rest_framework import viewsets, permissions
from .models import Store
from .serializers import StoreSerializer
from accounts.permissions import IsAdmin

class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if IsAdmin().has_permission(self.request, self):
            return Store.objects.all()
        return Store.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
