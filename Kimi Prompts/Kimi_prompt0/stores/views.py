"""Views for the stores app."""
from django.db.models import Q
from rest_framework import generics, permissions

from accounts.permissions import IsAdmin, IsSeller
from accounts.serializers import UserSerializer

from .models import Store
from .serializers import StoreSerializer


class StoreListView(generics.ListCreateAPIView):
    """List all active stores or create a store (seller only)."""

    serializer_class = StoreSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly
    ]
    queryset = Store.objects.filter(is_active=True)

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsSeller()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class StoreDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve a store, or update it if you're the owner or an admin."""

    serializer_class = StoreSerializer
    queryset = Store.objects.all()

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method in ("PUT", "PATCH"):
            user = request.user
            if not (user.is_admin_role or obj.owner_id == user.id):
                self.permission_denied(request)


class MyStoreView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the current seller's own store."""

    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if not user.is_seller and not user.is_admin_role:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only sellers can access their store.")
        return Store.objects.get(owner=user)


class StoreOwnerView(generics.RetrieveAPIView):
    """Retrieve the owner profile of a store."""

    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Store.objects.all()
    lookup_url_kwarg = "pk"

    def get_object(self):
        store = super().get_object()
        return store.owner


class AdminStoreListView(generics.ListAPIView):
    """Admin: list all stores including inactive ones."""

    serializer_class = StoreSerializer
    permission_classes = [IsAdmin]
    queryset = Store.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        active = self.request.query_params.get("active")
        if active is not None:
            qs = qs.filter(is_active=active.lower() == "true")
        return qs
