from rest_framework import serializers

from order.models import Order, OrderLine
from payment.models import Payment, Refund, RefundLine, TenderMethod


class RefundLineReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundLine
        fields = ("id", "refund", "order_line", "quantity", "disposition", "amount_cents", "returned_variant")
        read_only_fields = fields


class RefundReadSerializer(serializers.ModelSerializer):
    lines = RefundLineReadSerializer(many=True, read_only=True)
    order_number = serializers.CharField(source="order.number", read_only=True)
    processed_by_email = serializers.EmailField(source="processed_by.email", read_only=True)

    class Meta:
        model = Refund
        fields = (
            "id", "number", "order", "order_number", "payment", "credit_cents",
            "cash_refund_cents", "method", "reason", "processed_by",
            "processed_by_email", "processed_by_name", "idempotency_key",
            "lines", "created_at",
        )
        read_only_fields = fields


class RefundCreateLineSerializer(serializers.Serializer):
    order_line_id = serializers.PrimaryKeyRelatedField(source="order_line", queryset=OrderLine.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    disposition = serializers.ChoiceField(choices=RefundLine.Disposition.choices)


class RefundCreateSerializer(serializers.Serializer):
    order_id = serializers.PrimaryKeyRelatedField(source="order", queryset=Order.objects.all())
    order_version = serializers.IntegerField(min_value=1)
    payment_id = serializers.PrimaryKeyRelatedField(
        source="payment", queryset=Payment.objects.all(), allow_null=True, required=False,
    )
    lines = RefundCreateLineSerializer(many=True, allow_empty=False)
    method = serializers.ChoiceField(choices=TenderMethod.choices)
    reason = serializers.CharField(max_length=2000)

    def validate_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A refund reason is required.")
        return value
