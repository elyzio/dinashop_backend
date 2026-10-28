from django.urls import path
from catalog.views.product_variant import (
    ProductVariantBarcodeGenerateView,
    ProductVariantBarcodeLookupView,
    ProductVariantDetailView,
    ProductVariantListView,
    ProductVariantPricingView,
)
app_name = "product_variant"
urlpatterns = [
    path("", ProductVariantListView.as_view(), name="list"),
    path(
        "barcode-lookup/",
        ProductVariantBarcodeLookupView.as_view(),
        name="barcode-lookup",
    ),
    path("<uuid:pk>/", ProductVariantDetailView.as_view(), name="detail"),
    path("<uuid:pk>/pricing/", ProductVariantPricingView.as_view(), name="pricing"),
    path(
        "<uuid:pk>/barcode/generate/",
        ProductVariantBarcodeGenerateView.as_view(),
        name="barcode-generate",
    ),
]
