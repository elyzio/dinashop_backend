from django.urls import path
from catalog.views.variant_option_value import VariantOptionValueDetailView, VariantOptionValueListView
app_name = "variant_option_value"
urlpatterns = [path("", VariantOptionValueListView.as_view(), name="list"), path("<uuid:pk>/", VariantOptionValueDetailView.as_view(), name="detail")]
