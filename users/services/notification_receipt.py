from django.db import transaction
from django.utils import timezone

from users.models import NotificationReceipt


@transaction.atomic
def acknowledge_notification(*, user, notification_id, fingerprint, action):
    receipt, _ = NotificationReceipt.objects.select_for_update().get_or_create(
        user=user,
        notification_id=notification_id,
        fingerprint=fingerprint,
    )
    now = timezone.now()
    update_fields = ["updated_at"]
    if action == "read":
        receipt.read_at = receipt.read_at or now
        update_fields.append("read_at")
    else:
        receipt.dismissed_at = receipt.dismissed_at or now
        receipt.read_at = receipt.read_at or now
        update_fields.extend(("dismissed_at", "read_at"))
    receipt.save(update_fields=update_fields)
    return receipt


@transaction.atomic
def mark_notifications_read(*, user, items):
    return [
        acknowledge_notification(
            user=user,
            notification_id=item["notification_id"],
            fingerprint=item["fingerprint"],
            action="read",
        )
        for item in items
    ]
