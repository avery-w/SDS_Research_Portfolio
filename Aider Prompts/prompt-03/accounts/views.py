from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from ratelimit.decorators import ratelimit
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, RegistrationSerializer
from .permissions import IsAdmin
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

User = get_user_model()

@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class RateLimitedTokenObtainPairView(TokenObtainPairView):
    pass

class RateLimitedTokenRefreshView(TokenRefreshView):
    @ratelimit(key="ip", rate="10/m", block=True)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if IsAdmin().has_permission(self.request, self):
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

class RegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    @ratelimit(key="ip", rate="10/m", block=True)
    def post(self, request):
        ser = RegistrationSerializer(data=request.data)
        if ser.is_valid():
            user = ser.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
