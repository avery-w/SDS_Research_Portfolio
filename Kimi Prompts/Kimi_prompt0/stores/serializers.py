"""Serializers for the stores app."""
from rest_framework import serializers

from .models import Store


class StoreSerializer(serializers.ModelSerializer):
    """Serialize a store with its owner info."""

    owner_name = serializers.CharField(
        source="owner.username", read_only=True
    )

    class Meta:
        model = Store
        fields = [
            "id",
            "owner",
            "owner_name",
            "name",
            "slug",
            "description",
            "logo",
            "banner",
            "address",
            "city",
            "state",
            "postal_code",
            "country",
            "is_active",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "is_active", "is_verified", "created_at", "updated_at"]
