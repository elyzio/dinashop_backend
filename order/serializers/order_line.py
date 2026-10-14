from rest_framework import serializers

from catalog.models import ProductVariant
from order.models import OrderLine


class OrderLineReadSerializer(serializers.ModelSerializer):
    reservation_status = serializers.CharField(source="reservation.status", read_only=True, allow_null=True)

    class Meta:
        model = OrderLine
        fields = (
            "id", "order", "kind", "variant", "product_name",
            "variant_description", "sku", "description", "quantity",
            "unit_price_cents", "estimated_tax_cents", "actual_tax_cents",
            "landed_cost_cents", "reservation_status", "created_at",
        )
        read_only_fields = fields


class OrderLineCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=OrderLine.Kind.choices)
    variant_id = serializers.PrimaryKeyRelatedField(
        source="variant",
        queryset=ProductVariant.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )
    product_name = serializers.CharField(max_length=180, allow_blank=True, required=False, default="")
    description = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")
    quantity = serializers.IntegerField(min_value=1)
    unit_price_cents = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    estimated_tax_cents = serializers.IntegerField(min_value=0, allow_null=True, required=False)

    def validate(self, attrs):
        kind = attrs["kind"]
        variant = attrs.get("variant")
        price_supplied = attrs.get("unit_price_cents") is not None
        if kind == OrderLine.Kind.CATALOG and variant is None:
            raise serializers.ValidationError({"variant_id": "A catalog line requires a variant."})
        if kind == OrderLine.Kind.SPECIAL:
            if variant is not None:
                raise serializers.ValidationError({"variant_id": "Special lines cannot select a variant during order creation."})
            if not attrs.get("description", "").strip():
                raise serializers.ValidationError({"description": "Describe the requested item."})
            if not price_supplied:
                raise serializers.ValidationError({"unit_price_cents": "An estimated unit price is required."})
        return attrs


class SpecialLineReceiveSerializer(serializers.Serializer):
    total_product_cost_cents = serializers.IntegerField(min_value=0)
    tax_cents = serializers.IntegerField(min_value=0, required=False, default=0)
    fees_cents = serializers.IntegerField(min_value=0, required=False, default=0)
    note = serializers.CharField(allow_blank=True, required=False, default="")
