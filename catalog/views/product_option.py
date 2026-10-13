from rest_framework import generics

from catalog.models import ProductOption
from catalog.serializers.product_option import ProductOptionSerializer


class ProductOptionListView(generics.ListAPIView):
    queryset = ProductOption.objects.select_related("product").prefetch_related("values")
    serializer_class = ProductOptionSerializer
    filterset_fields = ("product",)
    search_fields = ("name", "product__name")
    ordering_fields = ("name", "sort_order")
    ordering = ("sort_order", "name")


class ProductOptionDetailView(generics.RetrieveAPIView):
    queryset = ProductOption.objects.select_related("product").prefetch_related("values")
    serializer_class = ProductOptionSerializer
