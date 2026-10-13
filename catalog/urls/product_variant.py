from django.urls import path
from catalog.views.product_variant import ProductVariantDetailView, ProductVariantListView, ProductVariantPricingView
app_name = "product_variant"
urlpatterns = [path("", ProductVariantListView.as_view(), name="list"), path("<uuid:pk>/", ProductVariantDetailView.as_view(), name="detail"), path("<uuid:pk>/pricing/", ProductVariantPricingView.as_view(), name="pricing")]
