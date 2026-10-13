from django.urls import path

from catalog.views.product import (
    ProductDetailView,
    ProductListCreateView,
    ProductVariantGridView,
    ProductVisibilityView,
)

app_name = "product"

urlpatterns = [
    path("", ProductListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/", ProductDetailView.as_view(), name="detail"),
    path("<uuid:pk>/variant-grid/", ProductVariantGridView.as_view(), name="variant-grid"),
    path("<uuid:pk>/visibility/", ProductVisibilityView.as_view(), name="visibility"),
]
