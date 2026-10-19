from django.utils import timezone
from rest_framework import serializers


class DateRangeQuerySerializer(serializers.Serializer):
    from_date = serializers.DateField(required=False, source="from")
    to_date = serializers.DateField(required=False, source="to")

    def to_internal_value(self, data):
        mutable = data.copy()
        if "from" in mutable:
            mutable["from_date"] = mutable.get("from")
        if "to" in mutable:
            mutable["to_date"] = mutable.get("to")
        return super().to_internal_value(mutable)

    def validate(self, attrs):
        today = timezone.localdate()
        start = attrs.get("from", today.replace(day=1))
        end = attrs.get("to", today)
        if start > end:
            raise serializers.ValidationError(
                {"from": "The start date cannot be after the end date."}
            )
        if (end - start).days > 3660:
            raise serializers.ValidationError(
                {"to": "The report range cannot exceed ten years."}
            )
        attrs["from"] = start
        attrs["to"] = end
        return attrs


class ReportColumnSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    kind = serializers.ChoiceField(
        choices=("text", "date", "datetime", "month", "integer", "money", "status")
    )


class ReportResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    currency = serializers.CharField()
    from_date = serializers.DateField(source="from")
    to_date = serializers.DateField(source="to")
    generated_at = serializers.DateTimeField()
    columns = ReportColumnSerializer(many=True)
    rows = serializers.ListField(child=serializers.DictField())


class DashboardMetricSerializer(serializers.Serializer):
    orders_to_deliver = serializers.IntegerField()
    active_orders = serializers.IntegerField()
    balance_due_cents = serializers.IntegerField()
    cod_cash_held_cents = serializers.IntegerField()
    profit_this_month_cents = serializers.IntegerField()
    profit_is_provisional = serializers.BooleanField()


class DashboardSpecialOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.CharField()
    customer_name = serializers.CharField()
    description = serializers.CharField()
    estimated_total_cents = serializers.IntegerField()
    special_status = serializers.CharField()


class DashboardAttentionSerializer(serializers.Serializer):
    kind = serializers.CharField()
    label = serializers.CharField()
    detail = serializers.CharField()
    entity_id = serializers.UUIDField()


class DashboardMonthlyProfitSerializer(serializers.Serializer):
    month = serializers.CharField()
    profit_cents = serializers.IntegerField()
    provisional = serializers.BooleanField()


class DashboardResponseSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    currency = serializers.CharField()
    metrics = DashboardMetricSerializer()
    special_orders = DashboardSpecialOrderSerializer(many=True)
    attention = DashboardAttentionSerializer(many=True)
    monthly_profit = DashboardMonthlyProfitSerializer(many=True)
