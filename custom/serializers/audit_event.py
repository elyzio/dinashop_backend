from rest_framework import serializers

from custom.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, allow_null=True)

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "actor",
            "actor_email",
            "action",
            "entity_type",
            "entity_id",
            "before",
            "after",
            "request_id",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields
