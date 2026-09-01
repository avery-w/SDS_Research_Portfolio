from rest_framework.permissions import BasePermission
from accounts.permissions import IsAdmin as _IsAdmin

class IsAdmin(_IsAdmin):
    pass

class IsSellerOrderItem(BasePermission):
    def has_object_permission(self, request, view, obj):
        # obj can be Order or OrderItem
        user = request.user
        if _IsAdmin().has_permission(request, view):
            return True
        if hasattr(obj, "store"):
            return obj.store.owner_id == user.id
        if hasattr(obj, "items"):
            return all(i.store.owner_id == user.id for i in obj.items.all())
        return False
