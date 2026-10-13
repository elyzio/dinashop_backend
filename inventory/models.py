import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class InventoryBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.OneToOneField(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="inventory",
    )
    in_hand = models.PositiveIntegerField(default=0)
    promised = models.PositiveIntegerField(default=0)
    last_landed_cost_cents = models.PositiveBigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(promised__lte=F("in_hand")),
                name="ck_inventory_promised_lte_in_hand",
            )
        ]

    @property
    def available(self):
        return self.in_hand - self.promised


class StockReservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONSUMED = "consumed", "Consumed"
        RELEASED = "released", "Released"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_line = models.OneToOneField(
        "order.OrderLine",
        on_delete=models.PROTECT,
        related_name="reservation",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="ck_reservation_quantity_positive",
            )
        ]
        indexes = [models.Index(fields=["variant", "status"])]


class StockMovement(models.Model):
    class Type(models.TextChoices):
        RECEIVED = "received", "Received"
        SOLD = "sold", "Sold"
        DAMAGED = "damaged", "Damaged"
        ADJUSTMENT = "adjustment", "Adjustment"
        REVERSAL = "reversal", "Reversal"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    movement_type = models.CharField(max_length=16, choices=Type.choices)
    quantity_delta = models.IntegerField()
    reference = models.CharField(max_length=120)
    order = models.ForeignKey(
        "order.Order",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    price_paid_cents = models.PositiveBigIntegerField(null=True, blank=True)
    tax_cents = models.PositiveBigIntegerField(null=True, blank=True)
    fees_cents = models.PositiveBigIntegerField(null=True, blank=True)
    landed_cost_cents = models.PositiveBigIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    idempotency_key = models.UUIDField(null=True, blank=True, unique=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(quantity_delta=0),
                name="ck_stock_movement_nonzero",
            )
        ]
        indexes = [
            models.Index(fields=["variant", "created_at"]),
            models.Index(fields=["movement_type", "created_at"]),
        ]
