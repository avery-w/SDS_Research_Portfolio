"""URL routes for the carts app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.MyCartView.as_view(), name="my-cart"),
    path("add/", views.AddItemView.as_view(), name="cart-add"),
    path("<int:pk>/", views.UpdateItemView.as_view(), name="cart-update"),
    path("remove/<int:pk>/", views.RemoveItemView.as_view(), name="cart-remove"),
    path("clear/", views.ClearCartView.as_view(), name="cart-clear"),
]
