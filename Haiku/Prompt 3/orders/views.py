from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
import uuid
from .models import Order, OrderItem, ReturnRequest, CancellationRequest, ShippingRate
from .serializers import OrderSerializer, ReturnRequestSerializer, CancellationRequestSerializer, ShippingRateSerializer
from core.models import Cart, Product, Store, UserProfile


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        profile = get_object_or_404(UserProfile, user=user)

        if profile.role == 'seller':
            return Order.objects.filter(items__store__seller=user).distinct()
        else:
            return Order.objects.filter(customer=user)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        from rest_framework_simplejwt.tokens import Token

        cart = get_object_or_404(Cart, customer=request.user)
        if not cart.items.exists():
            return Response({'detail': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        shipping_info = request.data.get('shipping_info')
        billing_info = request.data.get('billing_info', shipping_info)
        payment_method = request.data.get('payment_method', 'stripe')

        order_number = f"ORD-{uuid.uuid4().hex[:12].upper()}"

        total_price = sum(item.product.price * item.quantity for item in cart.items.all())
        shipping_price = self._calculate_shipping(cart.items.all())
        tax = total_price * 0.08

        order = Order.objects.create(
            customer=request.user,
            order_number=order_number,
            status='pending',
            total_price=total_price + shipping_price + tax,
            shipping_price=shipping_price,
            tax=tax,
            shipping_address=shipping_info.get('address'),
            shipping_city=shipping_info.get('city'),
            shipping_state=shipping_info.get('state'),
            shipping_zip=shipping_info.get('zip'),
            shipping_country=shipping_info.get('country', 'USA'),
            billing_address=billing_info.get('address'),
            billing_city=billing_info.get('city'),
            billing_state=billing_info.get('state'),
            billing_zip=billing_info.get('zip'),
            billing_country=billing_info.get('country', 'USA'),
            payment_method=payment_method,
            estimated_delivery=timezone.now() + timedelta(days=7),
        )

        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                store=cart_item.product.store,
                quantity=cart_item.quantity,
                price_at_purchase=cart_item.product.price,
            )
            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save()

        cart.items.all().delete()

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        orders = self.get_queryset().order_by('-created_at')
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def confirm_order(self, request, pk=None):
        order = self.get_object()
        profile = get_object_or_404(UserProfile, user=request.user)

        if profile.role != 'admin' and order.customer != request.user:
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        order.status = 'confirmed'
        order.payment_status = 'completed'
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    def _calculate_shipping(self, items):
        total_weight = sum(item.product.weight_kg * item.quantity for item in items)
        base_rate = ShippingRate.objects.filter(is_active=True).first()
        if base_rate:
            return float(base_rate.base_rate) + (float(total_weight) * float(base_rate.per_pound))
        return 0.0


class ReturnRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ReturnRequestSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        profile = get_object_or_404(UserProfile, user=user)

        if profile.role == 'admin':
            return ReturnRequest.objects.all()
        else:
            return ReturnRequest.objects.filter(order__customer=user)

    @action(detail=False, methods=['post'])
    def request_return(self, request):
        order_item_id = request.data.get('order_item_id')
        from orders.models import OrderItem
        order_item = get_object_or_404(OrderItem, id=order_item_id, order__customer=request.user)

        return_request = ReturnRequest.objects.create(
            order=order_item.order,
            order_item=order_item,
            reason=request.data.get('reason'),
            description=request.data.get('description'),
        )

        serializer = self.get_serializer(return_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CancellationRequestViewSet(viewsets.ModelViewSet):
    serializer_class = CancellationRequestSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        profile = get_object_or_404(UserProfile, user=user)

        if profile.role == 'admin':
            return CancellationRequest.objects.all()
        else:
            return CancellationRequest.objects.filter(order__customer=user)

    @action(detail=False, methods=['post'])
    def request_cancellation(self, request):
        order_id = request.data.get('order_id')
        order = get_object_or_404(Order, id=order_id, customer=request.user)

        if order.status != 'pending':
            return Response({'detail': 'Can only cancel pending orders'}, status=status.HTTP_400_BAD_REQUEST)

        cancellation = CancellationRequest.objects.create(
            order=order,
            reason=request.data.get('reason'),
        )

        serializer = self.get_serializer(cancellation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        cancellation = self.get_object()
        profile = get_object_or_404(UserProfile, user=request.user)

        if profile.role != 'admin':
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        order = cancellation.order
        order.status = 'cancelled'
        order.save()

        cancellation.status = 'approved'
        cancellation.refund_amount = order.total_price
        cancellation.save()

        serializer = self.get_serializer(cancellation)
        return Response(serializer.data)
