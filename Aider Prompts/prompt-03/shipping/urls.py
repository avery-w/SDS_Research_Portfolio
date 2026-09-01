from django.urls import path
from .views import RateQuoteView

urlpatterns = [
    path("rates/", RateQuoteView.as_view(), name="rates"),
]
