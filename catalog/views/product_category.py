from rest_framework import generics

from catalog.models import ProductCategory
from catalog.serializers.product_category import ProductCategorySerializer


class ProductCategoryListView(generics.ListAPIView):
    queryset = ProductCategory.objects.select_related("product", "category")
    serializer_class = ProductCategorySerializer
    filterset_fields = ("product", "category", "is_primary")
    ordering_fields = ("sort_order",)
    ordering = ("sort_order",)


class ProductCategoryDetailView(generics.RetrieveAPIView):
    queryset = ProductCategory.objects.select_related("product", "category")
    serializer_class = ProductCategorySerializer
