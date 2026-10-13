import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class TenderMethod(models.TextChoices):
    CASH = "cash", "Cash"
    BANK_TRANSFER = "bank_transfer", "Bank transfer"
    CARD = "card", "Card"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount_cents = models.PositiveBigIntegerField()
    receipt_number = models.CharField(max_length=30, unique=True)
    method = models.CharField(max_length=20, choices=TenderMethod.choices)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_payments",
    )
    received_by_name = models.CharField(max_length=160)
    tendered_cents = models.PositiveBigIntegerField(null=True, blank=True)
    change_cents = models.PositiveBigIntegerField(null=True, blank=True)
    external_reference = models.CharField(max_length=160, blank=True)
    idempotency_key = models.UUIDField(null=True, blank=True, unique=True)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_cents__gt=0),
                name="ck_payment_amount_positive",
            )
        ]
        indexes = [models.Index(fields=["order", "occurred_at"])]

    def clean(self):
        super().clean()
        if self.method == TenderMethod.CASH:
            if self.tendered_cents is None or self.tendered_cents < self.amount_cents:
                raise ValidationError({"tendered_cents": "Cash tendered must cover the payment."})
            expected_change = self.tendered_cents - self.amount_cents
            if self.change_cents != expected_change:
                raise ValidationError({"change_cents": "Cash change is inconsistent."})
        elif self.tendered_cents is not None or self.change_cents is not None:
            raise ValidationError("Tendered and change values are only valid for cash.")


class Refund(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=30, unique=True)
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.PROTECT,
        related_name="refunds",
    )
    payment = models.ForeignKey(
        "payment.Payment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="refunds",
    )
    credit_cents = models.PositiveBigIntegerField(default=0)
    cash_refund_cents = models.PositiveBigIntegerField(default=0)
    method = models.CharField(max_length=20, choices=TenderMethod.choices)
    reason = models.TextField()
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="processed_refunds",
    )
    processed_by_name = models.CharField(max_length=160)
    idempotency_key = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(credit_cents__gt=0) | Q(cash_refund_cents__gt=0),
                name="ck_refund_has_value",
            )
        ]
        indexes = [models.Index(fields=["order", "created_at"])]


class RefundLine(models.Model):
    class Disposition(models.TextChoices):
        RESTOCK = "restock", "Restock"
        DAMAGED = "damaged", "Damaged"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refund = models.ForeignKey(
        "payment.Refund",
        on_delete=models.PROTECT,
        related_name="lines",
    )
    order_line = models.ForeignKey(
        "order.OrderLine",
        on_delete=models.PROTECT,
        related_name="refund_lines",
    )
    quantity = models.PositiveIntegerField()
    disposition = models.CharField(max_length=12, choices=Disposition.choices)
    amount_cents = models.PositiveBigIntegerField()
    returned_variant = models.ForeignKey(
        "catalog.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="returned_lines",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["refund", "order_line"],
                name="uq_refund_order_line",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="ck_refund_line_quantity_positive",
            ),
        ]


class CodHandover(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    helper = models.ForeignKey(
        "people.Helper",
        on_delete=models.PROTECT,
        related_name="cod_handovers",
    )
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.PROTECT,
        related_name="cod_handovers",
    )
    amount_cents = models.PositiveBigIntegerField()
    handed_over_at = models.DateTimeField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_cod_handovers",
    )
    idempotency_key = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-handed_over_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_cents__gt=0),
                name="ck_cod_handover_amount_positive",
            )
        ]
        indexes = [
            models.Index(fields=["helper", "handed_over_at"]),
            models.Index(fields=["order", "handed_over_at"]),
        ]
