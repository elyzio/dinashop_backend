from rest_framework import serializers

from fulfillment.models import DeliveryJob
from order.models import Order
from people.models import Helper


class DeliveryJobReadSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)
    helper_name = serializers.CharField(source="helper.name", read_only=True)
    cod_collected_cents = serializers.IntegerField(source="cod_payment.amount_cents", read_only=True, allow_null=True)

    class Meta:
        model = DeliveryJob
        fields = (
            "id", "order", "order_number", "helper", "helper_name", "fee_cents",
            "fuel_cents", "status", "failure_reason", "status_changed_at",
            "created_by", "updated_by", "cod_payment", "cod_collected_cents",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class DeliveryJobCreateSerializer(serializers.Serializer):
    order_id = serializers.PrimaryKeyRelatedField(source="order", queryset=Order.objects.all())
    helper_id = serializers.PrimaryKeyRelatedField(source="helper", queryset=Helper.objects.all())
    fee_cents = serializers.IntegerField(min_value=0, required=False, default=0)
    fuel_cents = serializers.IntegerField(min_value=0, required=False, default=0)
    order_version = serializers.IntegerField(min_value=1)


class DeliveryVersionSerializer(serializers.Serializer):
    order_version = serializers.IntegerField(min_value=1)


class DeliveryFailSerializer(DeliveryVersionSerializer):
    failure_reason = serializers.CharField(max_length=2000)

    def validate_failure_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A failure reason is required.")
        return value
