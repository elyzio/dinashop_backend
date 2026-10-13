from django.urls import path
from catalog.views.product_option import ProductOptionDetailView, ProductOptionListView
app_name = "product_option"
urlpatterns = [path("", ProductOptionListView.as_view(), name="list"), path("<uuid:pk>/", ProductOptionDetailView.as_view(), name="detail")]
