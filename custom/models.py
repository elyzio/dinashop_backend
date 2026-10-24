import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class Category(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        HIDDEN = "hidden", "Hidden"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                name="uq_category_sibling_name",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["parent", "sort_order"]),
            models.Index(fields=["status", "name"]),
        ]

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        if self.parent_id == self.id:
            raise ValidationError({"parent": "A category cannot be its own parent."})

        visited = {self.id}
        ancestor_id = self.parent_id
        while ancestor_id is not None:
            if ancestor_id in visited:
                raise ValidationError({"parent": "A category hierarchy cannot contain a cycle."})
            visited.add(ancestor_id)
            ancestor_id = (
                Category.objects.filter(pk=ancestor_id)
                .values_list("parent_id", flat=True)
                .first()
            )

        duplicate = Category.objects.filter(
            parent_id=self.parent_id,
            name__iexact=self.name.strip(),
        ).exclude(pk=self.pk)
        if duplicate.exists():
            raise ValidationError({"name": "A sibling category with this name already exists."})

    def __str__(self):
        return self.name


class BusinessSettings(models.Model):
    """Singleton-like record selected by the fixed key `default`."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=30, default="default", unique=True, editable=False)
    business_name = models.CharField(max_length=160)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp_phone = models.CharField(max_length=32, blank=True)
    registration_id = models.CharField(max_length=80, blank=True)
    receipt_footer = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default="USD")
    timezone = models.CharField(max_length=64, default="UTC")
    low_stock_threshold = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "business settings"


class DocumentSequence(models.Model):
    """Lock this row when allocating human-readable document numbers."""

    key = models.CharField(max_length=30, primary_key=True)
    prefix = models.CharField(max_length=12)
    last_value = models.PositiveBigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def next_number(cls, *, key: str, prefix: str) -> str:
        with transaction.atomic():
            sequence = cls.objects.select_for_update().get(key=key)
            if sequence.prefix != prefix:
                raise ValueError(f"Sequence {key!r} is configured with another prefix.")
            sequence.last_value += 1
            sequence.save(update_fields=["last_value", "updated_at"])
            return f"{prefix}-{sequence.last_value:04d}"


class AuditEvent(models.Model):
    """Append-only record written by service functions after successful changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    action = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=80)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    request_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]
