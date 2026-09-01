from django.urls import path
from .views import CheckoutShippingQuote
urlpatterns = [path('quote/', CheckoutShippingQuote.as_view())]
