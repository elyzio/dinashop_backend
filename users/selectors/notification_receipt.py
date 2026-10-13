from users.models import NotificationReceipt


def notification_receipt_queryset(*, user):
    return NotificationReceipt.objects.filter(user=user)
