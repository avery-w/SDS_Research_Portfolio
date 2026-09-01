from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, MeView, MyCustomerProfileView, MySellerProfileView, AdminDeactivateUser

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('token/', TokenObtainPairView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('me/', MeView.as_view()),
    path('me/customer/', MyCustomerProfileView.as_view()),
    path('me/seller/', MySellerProfileView.as_view()),
    path('admin/deactivate/<int:user_id>/', AdminDeactivateUser.as_view()),
]
