from django.urls import path
from catalog.views.product_image import ProductImageDetailView, ProductImageListCreateView, ProductImageReorderView
app_name = "product_image"
urlpatterns = [path("", ProductImageListCreateView.as_view(), name="list-create"), path("reorder/", ProductImageReorderView.as_view(), name="reorder"), path("<uuid:pk>/", ProductImageDetailView.as_view(), name="detail")]
