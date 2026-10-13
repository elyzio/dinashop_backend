from rest_framework import serializers

from catalog.models import ProductOption
from catalog.serializers.product_option_value import ProductOptionValueSerializer


class ProductOptionSerializer(serializers.ModelSerializer):
    values = ProductOptionValueSerializer(many=True, read_only=True)

    class Meta:
        model = ProductOption
        fields = ("id", "product", "name", "sort_order", "values")
        read_only_fields = fields
