"""Views for the accounts app."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAdmin
from .serializers import (
    AdminUserUpdateSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Create a new user account and return an auth token."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Authenticate a user and return an auth token."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data}
        )


class LogoutView(APIView):
    """Invalidate the current user's auth token."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """View and update the currently authenticated user's profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """Admin: list all users with search and role filtering."""

    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get("role")
        search = self.request.query_params.get("search")
        if role:
            qs = qs.filter(role=role)
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        return qs.order_by("-date_joined")


class UserDetailView(generics.RetrieveUpdateAPIView):
    """Admin: retrieve/update a specific user's account."""

    serializer_class = AdminUserUpdateSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all()
    lookup_url_kwarg = "pk"


class DeactivateUserView(APIView):
    """Admin: deactivate (or reactivate) a user account."""

    permission_classes = [IsAdmin]

    def post(self, request, pk, *args, **kwargs):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return Response(UserSerializer(user).data)
