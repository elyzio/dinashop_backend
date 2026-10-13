from rest_framework import serializers

from catalog.models import ProductVariant
from inventory.models import StockMovement
from order.models import Order


class StockMovementSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    recorded_by_email = serializers.EmailField(source="recorded_by.email", read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "variant",
            "sku",
            "movement_type",
            "quantity_delta",
            "reference",
            "order",
            "price_paid_cents",
            "tax_cents",
            "fees_cents",
            "landed_cost_cents",
            "note",
            "idempotency_key",
            "recorded_by",
            "recorded_by_email",
            "created_at",
        )
        read_only_fields = fields


class StockReceiptSerializer(serializers.Serializer):
    variant_id = serializers.PrimaryKeyRelatedField(
        source="variant",
        queryset=ProductVariant.objects.filter(is_active=True),
    )
    quantity = serializers.IntegerField(min_value=1)
    price_paid_cents = serializers.IntegerField(min_value=0)
    tax_cents = serializers.IntegerField(min_value=0, required=False, default=0)
    fees_cents = serializers.IntegerField(min_value=0, required=False, default=0)
    order_id = serializers.PrimaryKeyRelatedField(
        source="order",
        queryset=Order.objects.all(),
        allow_null=True,
        required=False,
    )
    note = serializers.CharField(allow_blank=True, required=False, default="")


class StockAdjustmentSerializer(serializers.Serializer):
    REASONS = (
        ("damage", "Damage"),
        ("count_correction", "Count correction"),
        ("found_stock", "Found stock"),
        ("other", "Other"),
    )
    variant_id = serializers.PrimaryKeyRelatedField(
        source="variant",
        queryset=ProductVariant.objects.all(),
    )
    quantity_delta = serializers.IntegerField()
    reason = serializers.ChoiceField(choices=REASONS)
    note = serializers.CharField(allow_blank=True, required=False, default="")

    def validate(self, attrs):
        if attrs["quantity_delta"] == 0:
            raise serializers.ValidationError(
                {"quantity_delta": "Quantity delta cannot be zero."}
            )
        if attrs["reason"] == "damage" and attrs["quantity_delta"] > 0:
            raise serializers.ValidationError(
                {"quantity_delta": "Damage adjustments must reduce stock."}
            )
        return attrs
