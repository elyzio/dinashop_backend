from rest_framework import serializers

from order.models import Order
from order.serializers.order_line import OrderLineCreateSerializer, OrderLineReadSerializer
from order.services.totals import order_totals
from payment.models import TenderMethod
from people.models import Customer


class InitialPaymentSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=TenderMethod.choices)
    tendered_cents = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    external_reference = serializers.CharField(max_length=160, allow_blank=True, required=False, default="")
    occurred_at = serializers.DateTimeField(required=False)


class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.PrimaryKeyRelatedField(source="customer", queryset=Customer.objects.filter(is_active=True))
    lines = OrderLineCreateSerializer(many=True, allow_empty=False)
    discount_cents = serializers.IntegerField(min_value=0, required=False, default=0)
    delivery_method = serializers.ChoiceField(choices=Order.DeliveryMethod.choices)
    pickup_timing = serializers.ChoiceField(choices=Order.PickupTiming.choices, allow_null=True, required=False)
    delivery_address = serializers.CharField(allow_blank=True, required=False, default="")
    cod = serializers.BooleanField(required=False, default=False)
    customer_accepted_price_change = serializers.BooleanField(required=False, default=False)
    initial_payment = InitialPaymentSerializer(required=False)

    def validate(self, attrs):
        method = attrs["delivery_method"]
        if method == Order.DeliveryMethod.DELIVERY and not attrs.get("delivery_address", "").strip():
            raise serializers.ValidationError({"delivery_address": "A delivery address is required."})
        if method == Order.DeliveryMethod.PICKUP and not attrs.get("pickup_timing"):
            raise serializers.ValidationError({"pickup_timing": "Pickup timing is required."})
        if attrs.get("cod") and method != Order.DeliveryMethod.DELIVERY:
            raise serializers.ValidationError({"cod": "COD is only available for delivery orders."})
        return attrs


class OrderReadSerializer(serializers.ModelSerializer):
    lines = OrderLineReadSerializer(many=True, read_only=True)
    customer_id = serializers.UUIDField(read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    subtotal_cents = serializers.SerializerMethodField()
    total_cents = serializers.SerializerMethodField()
    paid_cents = serializers.SerializerMethodField()
    refunded_cents = serializers.SerializerMethodField()
    cash_refunded_cents = serializers.SerializerMethodField()
    balance_due_cents = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    is_estimate = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id", "number", "customer_id", "customer_name", "customer_phone",
            "created_by", "created_by_email", "status", "special_status", "lines",
            "discount_cents", "final_price_cents", "delivery_method", "pickup_timing",
            "delivery_address", "cod", "customer_accepted_price_change",
            "customer_notified_at", "fulfilled_at", "cancelled_at",
            "cancellation_reason", "subtotal_cents", "total_cents", "paid_cents",
            "refunded_cents", "cash_refunded_cents", "balance_due_cents",
            "payment_status", "is_estimate", "allowed_actions", "version",
            "created_at", "updated_at",
        )
        read_only_fields = fields

    def _totals(self, obj):
        cache = getattr(self, "_totals_cache", None)
        if cache is None:
            cache = self._totals_cache = {}
        return cache.setdefault(obj.pk, order_totals(obj))

    def get_subtotal_cents(self, obj) -> int: return self._totals(obj)["subtotal_cents"]
    def get_total_cents(self, obj) -> int: return self._totals(obj)["total_cents"]
    def get_paid_cents(self, obj) -> int: return self._totals(obj)["paid_cents"]
    def get_refunded_cents(self, obj) -> int: return self._totals(obj)["refunded_cents"]
    def get_cash_refunded_cents(self, obj) -> int: return self._totals(obj)["cash_refunded_cents"]
    def get_balance_due_cents(self, obj) -> int: return self._totals(obj)["balance_due_cents"]
    def get_payment_status(self, obj) -> str: return self._totals(obj)["payment_status"]
    def get_is_estimate(self, obj) -> bool: return bool(obj.special_status and obj.final_price_cents is None)

    def get_allowed_actions(self, obj) -> list[str]:
        if obj.status in (Order.Status.CANCELLED, Order.Status.COMPLETED):
            return []
        actions = []
        if obj.status == Order.Status.CONFIRMED:
            actions.append("cancel")
        if not obj.special_status and obj.status == Order.Status.CONFIRMED:
            actions.append("fulfill")
        if obj.special_status in (Order.SpecialStatus.REQUESTED, Order.SpecialStatus.QUOTED):
            actions.append("special_transition")
        if obj.special_status == Order.SpecialStatus.CONFIRMED:
            actions.append("receive_special")
        if obj.special_status == Order.SpecialStatus.ITEM_RECEIVED:
            actions.append("set_final_price")
        if obj.special_status == Order.SpecialStatus.FINAL_PRICE_SET:
            actions.extend(("mark_customer_notified", "decline"))
        if obj.special_status == Order.SpecialStatus.CUSTOMER_NOTIFIED and obj.delivery_method == Order.DeliveryMethod.PICKUP:
            actions.append("fulfill")
        if obj.fulfilled_at and self.get_balance_due_cents(obj) == 0:
            actions.append("complete")
        return actions


class VersionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class CancelOrderSerializer(VersionSerializer):
    reason = serializers.CharField(max_length=1000)

    def validate_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A cancellation reason is required.")
        return value


class SpecialTransitionSerializer(VersionSerializer):
    target = serializers.ChoiceField(choices=("quoted", "confirmed"))


class FinalPriceLineSerializer(serializers.Serializer):
    order_line_id = serializers.UUIDField()
    actual_tax_cents = serializers.IntegerField(min_value=0)


class SetFinalPriceSerializer(VersionSerializer):
    final_price_cents = serializers.IntegerField(min_value=0)
    lines = FinalPriceLineSerializer(many=True, required=False, default=list)


class CustomerNotifiedSerializer(VersionSerializer):
    accepted_price_change = serializers.BooleanField(required=False)


class DeclineOrderSerializer(VersionSerializer):
    method = serializers.ChoiceField(choices=TenderMethod.choices)
    reason = serializers.CharField(max_length=1000, required=False, default="Customer declined final price.")
