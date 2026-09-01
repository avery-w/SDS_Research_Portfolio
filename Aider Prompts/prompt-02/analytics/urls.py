from django.urls import path
from .views import AdminKpisView
urlpatterns = [path('kpis/', AdminKpisView.as_view())]
