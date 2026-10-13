from rest_framework import serializers

from inventory.models import InventoryBalance


class InventoryBalanceSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_id = serializers.UUIDField(source="variant.product_id", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    available = serializers.IntegerField(read_only=True)

    class Meta:
        model = InventoryBalance
        fields = (
            "id",
            "variant",
            "sku",
            "product_id",
            "product_name",
            "in_hand",
            "promised",
            "available",
            "last_landed_cost_cents",
            "updated_at",
        )
        read_only_fields = fields
