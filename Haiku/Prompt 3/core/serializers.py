from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Store, Product, ProductImage, Cart, CartItem, Review, Message
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'username')
        read_only_fields = ('id',)


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ('id', 'user', 'role', 'phone', 'address', 'city', 'state', 'zip_code', 'country', 'profile_image', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    role = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password2', 'role')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match."})
        return attrs

    def create(self, validated_data):
        role = validated_data.pop('role')
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            **validated_data
        )
        UserProfile.objects.create(user=user, role=role)
        return user


class StoreSerializer(serializers.ModelSerializer):
    seller = UserSerializer(read_only=True)

    class Meta:
        model = Store
        fields = ('id', 'seller', 'name', 'description', 'logo', 'banner', 'phone', 'email', 'address', 'city', 'state', 'zip_code', 'country', 'is_active', 'rating', 'created_at')
        read_only_fields = ('id', 'created_at', 'seller', 'rating')


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text', 'is_primary')
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    store = StoreSerializer(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'store', 'name', 'description', 'price', 'stock', 'sku', 'category', 'weight_kg', 'dimensions_length', 'dimensions_width', 'dimensions_height', 'rating', 'is_active', 'images', 'created_at')
        read_only_fields = ('id', 'created_at', 'rating')


class ProductDetailSerializer(ProductSerializer):
    reviews = serializers.SerializerMethodField()

    def get_reviews(self, obj):
        reviews = obj.reviews.all()[:5]
        return ReviewSerializer(reviews, many=True).data


class ReviewSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'customer', 'rating', 'title', 'content', 'helpful_count', 'created_at')
        read_only_fields = ('id', 'created_at', 'customer')


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'product_id', 'quantity', 'added_at')
        read_only_fields = ('id', 'added_at')


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'items', 'total_price', 'updated_at')
        read_only_fields = ('id', 'updated_at')

    def get_total_price(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'sender', 'recipient', 'subject', 'content', 'is_read', 'created_at', 'product')
        read_only_fields = ('id', 'created_at', 'sender')
