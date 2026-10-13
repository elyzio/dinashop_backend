from django.urls import path
from catalog.views.product_category import ProductCategoryDetailView, ProductCategoryListView
app_name = "product_category"
urlpatterns = [path("", ProductCategoryListView.as_view(), name="list"), path("<uuid:pk>/", ProductCategoryDetailView.as_view(), name="detail")]
