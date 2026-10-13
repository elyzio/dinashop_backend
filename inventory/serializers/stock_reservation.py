from rest_framework import serializers

from inventory.models import StockReservation


class StockReservationSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    order_id = serializers.UUIDField(source="order_line.order_id", read_only=True)

    class Meta:
        model = StockReservation
        fields = (
            "id",
            "order_line",
            "order_id",
            "variant",
            "sku",
            "quantity",
            "status",
            "created_at",
            "released_at",
            "consumed_at",
        )
        read_only_fields = fields
