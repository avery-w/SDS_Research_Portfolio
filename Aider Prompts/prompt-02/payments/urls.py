from django.urls import path
from .views import PaymentIntentView
urlpatterns = [path('intent/<uuid:order_id>/', PaymentIntentView.as_view())]
