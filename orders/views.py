from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from products.models import Product
from decimal import Decimal

# Mock UPS-based shipping calculation using origin 110 Inner Campus Drive, Austin, TX 78705
# This is a simplified, local calculation that mimics zone/weight behavior.

def mock_ups_rate(items, destination_zip):
    # items: list of dicts {'product': Product, 'quantity': int}
    base = Decimal('5.00')
    per_item = Decimal('1.50')
    total_items = sum(i['quantity'] for i in items)
    subtotal_weight_est = sum((i['product'].price * i['quantity']) for i in items) / Decimal('10')
    # simple distance factor from Austin ZIP prefix
    if str(destination_zip).startswith('78'):
        distance_factor = Decimal('1.0')
    else:
        distance_factor = Decimal('1.3')
    rate = base + per_item * Decimal(total_items) + Decimal(subtotal_weight_est) * distance_factor * Decimal('0.02')
    return rate.quantize(Decimal('0.01'))

class CheckoutAPIView(APIView):
    def post(self, request):
        payload = request.data
        items = payload.get('items', [])
        dest_zip = payload.get('destination_zip', '')
        if not items:
            return Response({'detail': 'Cart items required'}, status=status.HTTP_400_BAD_REQUEST)

        line_items = []
        subtotal = Decimal('0')
        for it in items:
            try:
                product = Product.objects.get(pk=it.get('product_id'))
            except Product.DoesNotExist:
                return Response({'detail': f"Product {it.get('product_id')} not found"}, status=status.HTTP_400_BAD_REQUEST)
            qty = int(it.get('quantity', 1))
            line_total = product.price * qty
            subtotal += line_total
            line_items.append({'product': product, 'quantity': qty})

        shipping_rate = mock_ups_rate(line_items, dest_zip)
        total = (subtotal + shipping_rate).quantize(Decimal('0.01'))

        return Response({
            'origin': '110 Inner Campus Drive, Austin, TX 78705',
            'destination_zip': dest_zip,
            'subtotal': f"{subtotal}",
            'shipping_rate': f"{shipping_rate}",
            'total': f"{total}",
        })
