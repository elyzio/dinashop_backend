from rest_framework import generics

from catalog.models import ProductOptionValue
from catalog.serializers.product_option_value import ProductOptionValueSerializer


class ProductOptionValueListView(generics.ListAPIView):
    queryset = ProductOptionValue.objects.select_related("option", "option__product")
    serializer_class = ProductOptionValueSerializer
    filterset_fields = ("option", "option__product")
    search_fields = ("value", "option__name")
    ordering_fields = ("value", "sort_order")
    ordering = ("sort_order", "value")


class ProductOptionValueDetailView(generics.RetrieveAPIView):
    queryset = ProductOptionValue.objects.select_related("option", "option__product")
    serializer_class = ProductOptionValueSerializer
