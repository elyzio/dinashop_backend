from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from custom.models import BusinessSettings
from custom.whatsapp import whatsapp_digits


class BusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSettings
        fields = (
            "id",
            "business_name",
            "address",
            "phone",
            "whatsapp_phone",
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

    def validate_whatsapp_phone(self, value):
        """Store an optional WhatsApp number as E.164-style digits.

        ``wa.me`` accepts digits only.  Keeping a leading ``+`` in the
        administrative value makes the country-code requirement clear while
        avoiding a separate public URL field.
        """
        value = value.strip()
        if not value:
            return ""
        digits = whatsapp_digits(value)
        if not 8 <= len(digits) <= 15:
            raise serializers.ValidationError(
                "Enter a WhatsApp number with country code (8 to 15 digits)."
            )
        return f"+{digits}"
