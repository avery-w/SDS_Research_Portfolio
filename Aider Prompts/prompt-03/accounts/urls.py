from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, RegistrationView, RateLimitedTokenObtainPairView, RateLimitedTokenRefreshView

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/token/", RateLimitedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", RateLimitedTokenRefreshView.as_view(), name="token_refresh"),
    path("register/", RegistrationView.as_view(), name="register"),
]
