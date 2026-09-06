"""Serializers for the accounts app."""
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.authtoken.models import Token

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serialize a user's public profile."""

    role = serializers.ChoiceField(choices=User.Role.choices, read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "avatar",
            "role",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["id", "role", "is_active", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    """Create a new marketplace user."""

    password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=User.Role.choices, default=User.Role.CUSTOMER
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password2",
            "first_name",
            "last_name",
            "phone",
            "role",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": "The two password fields must match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        role = validated_data.pop("role")
        user = User(**validated_data)
        user.set_password(password)
        user.role = role
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """Authenticate a user and return an auth token."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs["username"], password=attrs["password"]
        )
        if not user:
            raise serializers.ValidationError(
                "Unable to log in with provided credentials."
            )
        if not user.is_active:
            raise serializers.ValidationError("This account is deactivated.")
        attrs["user"] = user
        return attrs


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Admin-only serializer for managing user accounts."""

    role = serializers.ChoiceField(choices=User.Role.choices)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "avatar",
            "role",
            "is_active",
        ]
        read_only_fields = ["id"]
