from rest_framework import serializers

from users.models import NotificationReceipt


class NotificationReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationReceipt
        fields = (
            "id",
            "notification_id",
            "fingerprint",
            "read_at",
            "dismissed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class NotificationAcknowledgeSerializer(serializers.Serializer):
    ACTION_READ = "read"
    ACTION_DISMISS = "dismiss"
    notification_id = serializers.CharField(max_length=120)
    fingerprint = serializers.CharField(max_length=128)
    action = serializers.ChoiceField(choices=(ACTION_READ, ACTION_DISMISS))


class NotificationReadItemSerializer(serializers.Serializer):
    notification_id = serializers.CharField(max_length=120)
    fingerprint = serializers.CharField(max_length=128)


class NotificationReadAllSerializer(serializers.Serializer):
    items = NotificationReadItemSerializer(many=True, allow_empty=False)

    def validate_items(self, value):
        keys = [(item["notification_id"], item["fingerprint"]) for item in value]
        if len(keys) != len(set(keys)):
            raise serializers.ValidationError("Duplicate notification versions are not allowed.")
        return value
