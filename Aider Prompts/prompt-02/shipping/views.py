from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .services import quote_shipping_for_cart
from orders.models import Cart

class CheckoutShippingQuote(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def post(self, request):
        cart = Cart.objects.get_or_create(user=request.user)[0]
        data = quote_shipping_for_cart(cart, request.data.get('destination', {}))
        return Response(data)
