from django.urls import path

from storefront.views.product import PublicProductDetailView, PublicProductListView

app_name = "product"
urlpatterns = [
    path("", PublicProductListView.as_view(), name="list"),
    path("<slug:public_slug>/", PublicProductDetailView.as_view(), name="detail"),
]
