from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from accounts.permissions import IsAdmin
from .serializers import RegisterSerializer, CustomerProfileSerializer, SellerProfileSerializer
from .models import CustomerProfile, SellerProfile, User

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = RegisterSerializer
    def get_object(self): return self.request.user

class MyCustomerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerProfileSerializer
    def get_object(self): return CustomerProfile.objects.get(user=self.request.user)

class MySellerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = SellerProfileSerializer
    def get_object(self): return SellerProfile.objects.get(user=self.request.user)

class AdminDeactivateUser(APIView):
    permission_classes = [IsAdmin]
    def post(self, request, user_id):
        from django.contrib.auth import get_user_model
        U = get_user_model()
        u = U.objects.get(id=user_id); u.is_active = False; u.save()
        return Response({'status':'deactivated'})
