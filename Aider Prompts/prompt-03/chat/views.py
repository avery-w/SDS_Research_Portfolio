from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from ratelimit.decorators import ratelimit
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from catalog.models import Product
from .services import generate_reply
from django.db.models import Q

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        return Conversation.objects.filter(Q(customer=u) | Q(seller=u))

    def perform_create(self, serializer):
        # Only customers can start convo by default
        serializer.save(customer=self.request.user)

    def create(self, request, *args, **kwargs):
        seller_id = request.data.get("seller")
        product_id = request.data.get("product")
        if not seller_id:
            return Response({"detail": "seller required"}, status=status.HTTP_400_BAD_REQUEST)
        conv = Conversation.objects.create(customer=request.user, seller_id=seller_id, product_id=product_id)
        return Response(ConversationSerializer(conv).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        conv = self.get_object()
        if conv.customer_id != request.user.id and conv.seller_id != request.user.id:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        conv.is_open = bool(request.data.get("is_open", True))
        conv.save(update_fields=["is_open"])
        return Response(ConversationSerializer(conv).data)

class AssistantView(APIView):
    permission_classes = [permissions.AllowAny]

    @ratelimit(key="ip", rate="20/m", block=True)
    def post(self, request):
        q = (request.data.get("message") or "")[:1000]
        product_id = request.data.get("product_id")
        product = (
            Product.objects.filter(id=product_id, is_active=True)
            .select_related("store__owner")
            .only("id", "title", "description", "store__owner_id")
            .first()
            if product_id
            else None
        )
        context = f"Product: {product.title}\nDescription: {product.description[:500]}" if product else ""
        reply = generate_reply(q, context)
        seller_id = product.store.owner_id if product else None
        return Response({"reply": reply, "suggest_contact_seller": bool(seller_id), "seller_id": seller_id, "product_id": product_id})
