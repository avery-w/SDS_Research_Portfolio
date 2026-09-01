from rest_framework import viewsets, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Cart, CartItem, Order, CancellationRequest, ReturnRequest
from .serializers import CartSerializer, CartItemSerializer, OrderSerializer, CancellationRequestSerializer, ReturnRequestSerializer
from accounts.permissions import IsCustomer, IsSeller, IsAdmin
from .services import create_order_from_cart
from shipping.services import quote_shipping_for_cart

class CartViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    serializer_class = CartSerializer
    def get_object(self): return Cart.objects.get_or_create(user=self.request.user)[0]

    @action(detail=False, methods=['post'])
    def add(self, request):
        s = CartItemSerializer(data=request.data); s.is_valid(raise_exception=True)
        item = CartItem.objects.update_or_create(cart=self.get_object(), product=s.validated_data['product'], defaults={'quantity': s.validated_data['quantity']})[0]
        return Response(CartItemSerializer(item).data, status=201)

    @action(detail=False, methods=['post'])
    def update_qty(self, request):
        s = CartItemSerializer(data=request.data); s.is_valid(raise_exception=True)
        item = CartItem.objects.get(cart=self.get_object(), product=s.validated_data['product'])
        item.quantity = s.validated_data['quantity']; item.save()
        return Response(CartItemSerializer(item).data)

    @action(detail=False, methods=['post'])
    def remove(self, request):
        s = CartItemSerializer(data=request.data); s.is_valid(raise_exception=True)
        CartItem.objects.filter(cart=self.get_object(), product=s.validated_data['product']).delete()
        return Response(status=204)

    @action(detail=False, methods=['post'], permission_classes=[IsCustomer])
    def shipping_quotes(self, request):
        return Response(quote_shipping_for_cart(self.get_object(), request.data.get('destination', {})))

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    def get_queryset(self):
        u = self.request.user
        if u.role == 'seller': return Order.objects.filter(store__owner=u)
        if u.role == 'admin': return Order.objects.all()
        return Order.objects.filter(customer=u)

    @action(detail=False, methods=['post'], permission_classes=[IsCustomer])
    def checkout(self, request):
        cart = Cart.objects.get_or_create(user=request.user)[0]
        shipping = request.data.get('shipping', {})
        shipping_cents = int(shipping.get('amount_cents', 0))
        tax_cents = 0  # plug-in tax calc here
        order = create_order_from_cart(cart, store=request.data.get('store'), shipping_address=shipping.get('address'), shipping_cents=shipping_cents, tax_cents=tax_cents)
        return Response(OrderSerializer(order).data, status=201)

class CancellationViewSet(viewsets.ModelViewSet):
    serializer_class = CancellationRequestSerializer
    def get_queryset(self):
        u = self.request.user
        if u.role == 'seller': return CancellationRequest.objects.filter(order__store__owner=u)
        if u.role == 'admin': return CancellationRequest.objects.all()
        return CancellationRequest.objects.filter(order__customer=u)

class ReturnViewSet(viewsets.ModelViewSet):
    serializer_class = ReturnRequestSerializer
    def get_queryset(self):
        u = self.request.user
        if u.role == 'seller': return ReturnRequest.objects.filter(order__store__owner=u)
        if u.role == 'admin': return ReturnRequest.objects.all()
        return ReturnRequest.objects.filter(order__customer=u)
