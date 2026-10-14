from django.utils import timezone
from rest_framework import serializers

from order.models import Order
from payment.models import CodHandover
from people.models import Helper


class CodHandoverReadSerializer(serializers.ModelSerializer):
    helper_name = serializers.CharField(source="helper.name", read_only=True)
    order_number = serializers.CharField(source="order.number", read_only=True)
    recorded_by_email = serializers.EmailField(source="recorded_by.email", read_only=True)

    class Meta:
        model = CodHandover
        fields = (
            "id", "helper", "helper_name", "order", "order_number", "amount_cents",
            "handed_over_at", "recorded_by", "recorded_by_email", "idempotency_key", "created_at",
        )
        read_only_fields = fields


class CodHandoverRecordSerializer(serializers.Serializer):
    helper_id = serializers.PrimaryKeyRelatedField(source="helper", queryset=Helper.objects.all())
    order_id = serializers.PrimaryKeyRelatedField(source="order", queryset=Order.objects.all())
    amount_cents = serializers.IntegerField(min_value=1)
    handed_over_at = serializers.DateTimeField(required=False, default=timezone.now)
