from django.urls import path
from .views import RateView

urlpatterns = [path('rates/', RateView.as_view())]
