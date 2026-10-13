from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from custom.models import BusinessSettings


class BusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSettings
        fields = (
            "id",
            "business_name",
            "address",
            "phone",
            "registration_id",
            "receipt_footer",
            "currency",
            "timezone",
            "low_stock_threshold",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_business_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Business name cannot be empty.")
        return value

    def validate_currency(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError(
                "Currency must contain exactly three letters."
            )
        return value

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise serializers.ValidationError("Use a valid IANA timezone.") from exc
        return value
