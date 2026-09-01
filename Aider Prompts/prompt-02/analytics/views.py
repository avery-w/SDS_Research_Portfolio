from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsAdmin
from orders.models import Order, OrderItem
from django.db.models import Sum, Count, F

class AdminKpisView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    def get(self, request):
        gmvc = Order.objects.filter(status__in=['paid','fulfilled']).aggregate(s=Sum('total_cents'))['s'] or 0
        orders = Order.objects.count()
        aov = (gmvc / orders) if orders else 0
        top_products = list(OrderItem.objects.values(t=F('title_snapshot')).annotate(q=Sum('quantity')).order_by('-q')[:10])
        return Response({'gmv_cents': gmvc, 'orders': orders, 'aov_cents': int(aov), 'top_products': top_products})
