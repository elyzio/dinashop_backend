import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class DeliveryJob(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "order.Order",
        on_delete=models.PROTECT,
        related_name="delivery_job",
    )
    helper = models.ForeignKey(
        "people.Helper",
        on_delete=models.PROTECT,
        related_name="delivery_jobs",
    )
    fee_cents = models.PositiveBigIntegerField(default=0)
    fuel_cents = models.PositiveBigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    failure_reason = models.TextField(blank=True)
    status_changed_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_delivery_jobs",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_delivery_jobs",
    )
    cod_payment = models.OneToOneField(
        "payment.Payment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cod_delivery_job",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["helper", "status"]),
        ]

    def clean(self):
        super().clean()
        if self.status == self.Status.FAILED and not self.failure_reason.strip():
            raise ValidationError({"failure_reason": "A failed delivery requires a reason."})
        if self.status != self.Status.FAILED and self.failure_reason.strip():
            raise ValidationError({"failure_reason": "Only failed deliveries have a failure reason."})
        if self.order_id and self.order.delivery_method != self.order.DeliveryMethod.DELIVERY:
            raise ValidationError({"order": "Only delivery orders can have delivery jobs."})
