from rest_framework import serializers

from custom.models import DocumentSequence


class DocumentSequenceSerializer(serializers.ModelSerializer):
    """Internal representation; document sequences have no public API view."""

    class Meta:
        model = DocumentSequence
        fields = ("key", "prefix", "last_value", "updated_at")
        read_only_fields = fields
