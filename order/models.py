import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        DELIVERED_PICKED_UP = "delivered_picked_up", "Delivered/Picked up"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class SpecialStatus(models.TextChoices):
        REQUESTED = "requested", "Requested"
        QUOTED = "quoted", "Quoted"
        CONFIRMED = "confirmed", "Confirmed"
        ITEM_RECEIVED = "item_received", "Item received"
        FINAL_PRICE_SET = "final_price_set", "Final price set"
        CUSTOMER_NOTIFIED = "customer_notified", "Customer notified"
        DELIVERED_PICKED_UP = "delivered_picked_up", "Delivered/Picked up"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        DECLINED = "declined", "Declined"

    class DeliveryMethod(models.TextChoices):
        DELIVERY = "delivery", "Delivery"
        PICKUP = "pickup", "Pickup"

    class PickupTiming(models.TextChoices):
        NOW = "now", "Now"
        LATER = "later", "Later"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.UUIDField(null=True, blank=True, unique=True)
    number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(
        "people.Customer",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_orders",
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.CONFIRMED)
    special_status = models.CharField(
        max_length=24,
        choices=SpecialStatus.choices,
        null=True,
        blank=True,
    )
    discount_cents = models.PositiveBigIntegerField(default=0)
    final_price_cents = models.PositiveBigIntegerField(null=True, blank=True)
    delivery_method = models.CharField(max_length=12, choices=DeliveryMethod.choices)
    pickup_timing = models.CharField(
        max_length=12,
        choices=PickupTiming.choices,
        null=True,
        blank=True,
    )
    delivery_address = models.TextField(blank=True)
    customer_name = models.CharField(max_length=160)
    customer_phone = models.CharField(max_length=40, blank=True)
    cod = models.BooleanField(default=False)
    customer_accepted_price_change = models.BooleanField(default=False)
    customer_notified_at = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["special_status", "created_at"]),
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["delivery_method", "status"]),
        ]

    def clean(self):
        super().clean()
        if self.delivery_method == self.DeliveryMethod.DELIVERY and not self.delivery_address.strip():
            raise ValidationError({"delivery_address": "A delivery address is required."})
        if self.delivery_method == self.DeliveryMethod.PICKUP and not self.pickup_timing:
            raise ValidationError({"pickup_timing": "Pickup timing is required."})
        if self.cod and self.delivery_method != self.DeliveryMethod.DELIVERY:
            raise ValidationError({"cod": "COD is only available for delivery orders."})

    def __str__(self):
        return self.number


class OrderLine(models.Model):
    class Kind(models.TextChoices):
        CATALOG = "catalog", "Catalog"
        SPECIAL = "special", "Special"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.PROTECT,
        related_name="lines",
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="order_lines",
    )
    product_name = models.CharField(max_length=180, blank=True)
    variant_description = models.CharField(max_length=240, blank=True)
    sku = models.CharField(max_length=80, blank=True)
    description = models.CharField(max_length=500)
    quantity = models.PositiveIntegerField()
    unit_price_cents = models.PositiveBigIntegerField()
    estimated_tax_cents = models.PositiveBigIntegerField(null=True, blank=True)
    actual_tax_cents = models.PositiveBigIntegerField(null=True, blank=True)
    landed_cost_cents = models.PositiveBigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="ck_order_line_quantity_positive",
            )
        ]
        indexes = [models.Index(fields=["order", "kind"])]

    def clean(self):
        super().clean()
        if self.kind == self.Kind.CATALOG and self.variant_id is None:
            raise ValidationError({"variant": "A catalog line requires a variant."})
        # Special lines begin without a variant. The receiving service later assigns
        # a server-generated hidden variant so stock can be reserved and traced.
