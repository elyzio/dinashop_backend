from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from custom.models import BusinessSettings
from custom.whatsapp import whatsapp_digits


class PublicStorefrontSerializer(serializers.ModelSerializer):
    whatsapp_url = serializers.SerializerMethodField()
    location_url = serializers.SerializerMethodField()

    class Meta:
        model = BusinessSettings
        fields = (
            "business_name",
            "currency",
            "address",
            "phone",
            "email",
            "whatsapp_url",
            "location_url",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_whatsapp_url(self, obj):
        digits = whatsapp_digits(obj.whatsapp_phone)
        if not 8 <= len(digits) <= 15:
            return None
        return f"https://wa.me/{digits}"

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_location_url(self, obj):
        if obj.latitude is None or obj.longitude is None:
            return None
        return (
            "https://www.google.com/maps/search/?api=1&query="
            f"{obj.latitude:f},{obj.longitude:f}"
        )
