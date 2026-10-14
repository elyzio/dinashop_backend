from django.utils import timezone
from rest_framework import serializers

from order.models import Order
from payment.models import Payment, TenderMethod


class PaymentReadSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)
    received_by_email = serializers.EmailField(source="received_by.email", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id", "order", "order_number", "amount_cents", "receipt_number",
            "method", "received_by", "received_by_email", "received_by_name",
            "tendered_cents", "change_cents", "external_reference",
            "idempotency_key", "occurred_at", "created_at",
        )
        read_only_fields = fields


class PaymentRecordSerializer(serializers.Serializer):
    order_id = serializers.PrimaryKeyRelatedField(source="order", queryset=Order.objects.all())
    order_version = serializers.IntegerField(min_value=1)
    amount_cents = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=TenderMethod.choices)
    tendered_cents = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    external_reference = serializers.CharField(max_length=160, allow_blank=True, required=False, default="")
    occurred_at = serializers.DateTimeField(required=False, default=timezone.now)

    def validate(self, attrs):
        if attrs["method"] == TenderMethod.CASH:
            if attrs.get("tendered_cents") is None:
                raise serializers.ValidationError({"tendered_cents": "Cash tendered is required."})
        elif attrs.get("tendered_cents") is not None:
            raise serializers.ValidationError({"tendered_cents": "Tendered cash is only valid for cash payments."})
        return attrs
