"""URL routes for the catalog app."""
from django.urls import path

from . import views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path(
        "categories/<int:pk>/",
        views.CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path(
        "products/mine/",
        views.MyProductsView.as_view(),
        name="my-products",
    ),
    path(
        "products/admin/all/",
        views.AdminProductListView.as_view(),
        name="admin-product-list",
    ),
    path(
        "products/<int:pk>/inventory/",
        views.ProductInventoryView.as_view(),
        name="product-inventory",
    ),
    path(
        "products/<int:pk>/images/",
        views.ProductImageView.as_view(),
        name="product-images",
    ),
    path(
        "products/<slug:slug>/",
        views.ProductDetailView.as_view(),
        name="product-detail",
    ),
]
