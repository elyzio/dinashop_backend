from rest_framework import serializers

from catalog.models import PriceHistory


class PriceHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = PriceHistory
        fields = (
            "id",
            "variant",
            "kind",
            "previous_cents",
            "new_cents",
            "sale_starts_at",
            "sale_ends_at",
            "changed_by",
            "changed_by_email",
            "changed_at",
        )
        read_only_fields = fields
