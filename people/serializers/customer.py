from rest_framework import serializers

from order.services.totals import balance_due_cents
from people.models import Customer, normalize_phone


class CustomerReadSerializer(serializers.ModelSerializer):
    order_count = serializers.SerializerMethodField()
    outstanding_cents = serializers.SerializerMethodField()
    duplicate_phone_warning = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = (
            "id", "name", "phone", "normalized_phone", "address", "note",
            "is_active", "is_walk_in", "order_count", "outstanding_cents",
            "duplicate_phone_warning", "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_order_count(self, obj) -> int:
        return len(obj.orders.all())

    def get_outstanding_cents(self, obj) -> int:
        return sum(balance_due_cents(order) for order in obj.orders.all())

    def get_duplicate_phone_warning(self, obj) -> dict | None:
        if not obj.normalized_phone:
            return None
        duplicate = Customer.objects.filter(
            normalized_phone=obj.normalized_phone,
        ).exclude(pk=obj.pk).first()
        return (
            {"customer_id": str(duplicate.id), "name": duplicate.name}
            if duplicate else None
        )


class CustomerWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    phone = serializers.CharField(max_length=40, allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)
    note = serializers.CharField(allow_blank=True, required=False)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value

    def validate_phone(self, value):
        value = value.strip()
        if value and not normalize_phone(value).lstrip("+").isdigit():
            raise serializers.ValidationError("Enter a valid phone number.")
        return value
