from django.urls import include, path

app_name = "catalog"

urlpatterns = [
    path("product/", include("catalog.urls.product")),
    path("product-category/", include("catalog.urls.product_category")),
    path("product-image/", include("catalog.urls.product_image")),
    path("product-option/", include("catalog.urls.product_option")),
    path("product-option-value/", include("catalog.urls.product_option_value")),
    path("product-variant/", include("catalog.urls.product_variant")),
    path("variant-option-value/", include("catalog.urls.variant_option_value")),
    path("price-history/", include("catalog.urls.price_history")),
]
