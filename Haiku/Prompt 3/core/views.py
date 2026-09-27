from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from .models import UserProfile, Store, Product, ProductImage, Cart, CartItem, Review, Message
from .serializers import (
    UserSerializer, UserProfileSerializer, UserRegistrationSerializer,
    StoreSerializer, ProductSerializer, ProductDetailSerializer, CartSerializer,
    CartItemSerializer, ReviewSerializer, MessageSerializer
)
from .chatbot import MarketplaceChatbot


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def me(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.filter(is_active=True)
    serializer_class = StoreSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [SearchFilter]
    search_fields = ['name', 'description']

    @action(detail=False, methods=['get'])
    def my_store(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        if profile.role != 'seller':
            return Response({'detail': 'Only sellers can access stores.'}, status=status.HTTP_403_FORBIDDEN)
        store = get_object_or_404(Store, seller=request.user)
        serializer = self.get_serializer(store)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['store', 'category']
    search_fields = ['name', 'description', 'sku']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer

    @action(detail=False, methods=['get'])
    def my_products(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        if profile.role != 'seller':
            return Response({'detail': 'Only sellers can access products.'}, status=status.HTTP_403_FORBIDDEN)
        products = Product.objects.filter(store__seller=request.user)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Cart.objects.filter(customer=self.request.user)

    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        cart, created = Cart.objects.get_or_create(customer=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart, _ = Cart.objects.get_or_create(customer=request.user)
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        product = get_object_or_404(Product, id=product_id)

        if product.stock < quantity:
            return Response({'detail': 'Not enough stock'}, status=status.HTTP_400_BAD_REQUEST)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response({'message': 'Item added to cart'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        cart = get_object_or_404(Cart, customer=request.user)
        product_id = request.data.get('product_id')
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
        return Response({'message': 'Item removed from cart'})


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = (IsAuthenticated,)

    @action(detail=False, methods=['post'])
    def create_review(self, request):
        product_id = request.data.get('product_id')
        product = get_object_or_404(Product, id=product_id)

        review, created = Review.objects.update_or_create(
            product=product,
            customer=request.user,
            defaults={
                'rating': request.data.get('rating'),
                'title': request.data.get('title'),
                'content': request.data.get('content'),
            }
        )

        serializer = self.get_serializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Message.objects.filter(recipient=self.request.user) | Message.objects.filter(sender=self.request.user)

    @action(detail=False, methods=['post'])
    def send_message(self, request):
        recipient_id = request.data.get('recipient_id')
        recipient = get_object_or_404(User, id=recipient_id)

        product_id = request.data.get('product_id')
        product = None
        if product_id:
            product = get_object_or_404(Product, id=product_id)

        message = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            product=product,
            subject=request.data.get('subject'),
            content=request.data.get('content'),
        )

        serializer = self.get_serializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def inbox(self, request):
        messages = Message.objects.filter(recipient=request.user).order_by('-created_at')
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        message_id = request.data.get('message_id')
        message = get_object_or_404(Message, id=message_id, recipient=request.user)
        message.is_read = True
        message.save()
        return Response({'message': 'Message marked as read'})


class ChatbotViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny,)

    @action(detail=False, methods=['post'], url_path='chat')
    def chat(self, request):
        user_message = request.data.get('message')
        product_id = request.data.get('product_id')

        if not user_message:
            return Response({'detail': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        product = None
        if product_id:
            product = get_object_or_404(Product, id=product_id)

        chatbot = MarketplaceChatbot()
        response = chatbot.process_message(
            user_message,
            user=request.user if request.user.is_authenticated else None,
            product=product
        )

        return Response({'response': response}, status=status.HTTP_200_OK)
