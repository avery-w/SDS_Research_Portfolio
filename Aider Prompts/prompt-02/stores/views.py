from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.permissions import IsSeller, IsAdmin
from .models import Store
from .serializers import StoreSerializer

class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    queryset = Store.objects.all()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        if self.action in ('destroy', 'deactivate', 'activate'):
            return [IsAdmin()]
        return [IsSeller()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.role == 'seller':
            return Store.objects.filter(owner=self.request.user)
        if self.request.user.is_authenticated and self.request.user.role == 'admin':
            return Store.objects.all()
        return Store.objects.filter(is_active=True)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def deactivate(self, request, pk=None):
        store = self.get_object()
        store.is_active = False
        store.save()
        return Response({'status': 'deactivated'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def activate(self, request, pk=None):
        store = self.get_object()
        store.is_active = True
        store.save()
        return Response({'status': 'activated'})
