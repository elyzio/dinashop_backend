from django.urls import path
from catalog.views.product_option_value import ProductOptionValueDetailView, ProductOptionValueListView
app_name = "product_option_value"
urlpatterns = [path("", ProductOptionValueListView.as_view(), name="list"), path("<uuid:pk>/", ProductOptionValueDetailView.as_view(), name="detail")]
