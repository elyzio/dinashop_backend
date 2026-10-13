from rest_framework import serializers

from catalog.models import VariantOptionValue


class VariantOptionValueSerializer(serializers.ModelSerializer):
    option_name = serializers.CharField(source="option.name", read_only=True)
    value_name = serializers.CharField(source="value.value", read_only=True)

    class Meta:
        model = VariantOptionValue
        fields = (
            "id",
            "variant",
            "option",
            "option_name",
            "value",
            "value_name",
        )
        read_only_fields = fields
