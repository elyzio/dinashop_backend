from rest_framework import generics

from catalog.models import VariantOptionValue
from catalog.serializers.variant_option_value import VariantOptionValueSerializer


class VariantOptionValueListView(generics.ListAPIView):
    queryset = VariantOptionValue.objects.select_related("variant", "option", "value")
    serializer_class = VariantOptionValueSerializer
    filterset_fields = ("variant", "variant__product", "option", "value")


class VariantOptionValueDetailView(generics.RetrieveAPIView):
    queryset = VariantOptionValue.objects.select_related("variant", "option", "value")
    serializer_class = VariantOptionValueSerializer
