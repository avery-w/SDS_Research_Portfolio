"""URL routes for the stores app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.StoreListView.as_view(), name="store-list"),
    path("mine/", views.MyStoreView.as_view(), name="my-store"),
    path("<slug:slug>/", views.StoreDetailView.as_view(), name="store-detail"),
    path("<int:pk>/owner/", views.StoreOwnerView.as_view(), name="store-owner"),
    path(
        "admin/all/",
        views.AdminStoreListView.as_view(),
        name="admin-store-list",
    ),
]
