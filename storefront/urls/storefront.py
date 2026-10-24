from django.urls import path

from storefront.views.storefront import PublicStorefrontView

app_name = "storefront"
urlpatterns = [path("", PublicStorefrontView.as_view(), name="detail")]
