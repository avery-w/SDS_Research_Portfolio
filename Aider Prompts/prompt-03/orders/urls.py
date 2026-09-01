from django.urls import path
from .views import CheckoutView, CancelView, ReturnRequestView

urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("<str:number>/cancel/", CancelView.as_view(), name="order-cancel"),
    path("returns/", ReturnRequestView.as_view(), name="order-return"),
]
