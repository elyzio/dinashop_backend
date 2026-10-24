from django.urls import include, path

app_name = "public"

urlpatterns = [
    path("storefront/", include("storefront.urls.storefront")),
    path("category/", include("storefront.urls.category")),
    path("product/", include("storefront.urls.product")),
]
