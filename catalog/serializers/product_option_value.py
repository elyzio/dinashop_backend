from rest_framework import serializers

from catalog.models import ProductOptionValue


class ProductOptionValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOptionValue
        fields = ("id", "option", "value", "sort_order")
        read_only_fields = fields
