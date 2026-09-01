import bleach
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CustomerProfile, SellerProfile

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ('username','email','password','role','first_name','last_name')
    def validate_username(self, v): return bleach.clean(v, strip=True)
    def create(self, validated):
        pwd = validated.pop('password')
        user = User(**validated)
        user.set_password(pwd)
        user.save()
        return user

class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta: model = CustomerProfile; fields = ('default_shipping_address',)

class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta: model = SellerProfile; fields = ('kyc_status','payout_account')
