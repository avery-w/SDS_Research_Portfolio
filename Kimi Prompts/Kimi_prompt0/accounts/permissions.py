"""Permission classes for role-based access control."""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    """Allow access only to admin-role users (or superusers)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_admin_role or user.is_superuser)
        )


class IsSeller(BasePermission):
    """Allow access only to seller-role users and admins."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_seller or user.is_admin_role)
        )


class IsSellerOrAdmin(BasePermission):
    """Allow sellers (own store) and admins."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)


class IsOwnerOrAdmin(BasePermission):
    """Allow access if the object is owned by the user or user is admin."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin_role:
            return True
        owner = getattr(obj, "user", None)
        if owner is not None and hasattr(owner, "id"):
            return owner.id == user.id
        return False
