import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from .upload_paths import product_image_rendition_upload_path, product_image_upload_path
from django.db.models import Q
from django.utils import timezone


class Product(models.Model):
    class Visibility(models.TextChoices):
        ACTIVE = "active", "Active"
        HIDDEN = "hidden", "Hidden"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=120, blank=True)
    # Public URLs use this immutable value instead of exposing an operational
    # identifier.  It is assigned by the product service when the product is
    # first created and is deliberately not updated when the name changes.
    public_slug = models.SlugField(max_length=200, unique=True, editable=False)
    visibility = models.CharField(
        max_length=12,
        choices=Visibility.choices,
        default=Visibility.ACTIVE,
    )
    has_variants = models.BooleanField(default=False)
    categories = models.ManyToManyField(
        "custom.Category",
        through="catalog.ProductCategory",
        related_name="products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["visibility", "name"]),
            models.Index(fields=["brand", "name"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.public_slug:
            # Admin and management code can create products outside the DRF
            # aggregate service, so keep the public URL invariant at model
            # level too. The public slug remains unchanged after creation.
            from catalog.services.public_slug import generate_public_slug

            self.public_slug = generate_public_slug(self.name)
        return super().save(*args, **kwargs)


class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="category_links",
    )
    category = models.ForeignKey(
        "custom.Category",
        on_delete=models.PROTECT,
        related_name="product_links",
    )
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "category_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "category"],
                name="uq_product_category",
            ),
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_primary=True),
                name="uq_product_primary_category",
            ),
        ]


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to=product_image_upload_path,
        width_field="width",
        height_field="height",
    )
    width = models.PositiveIntegerField(
        editable=False,
        null=True,
        blank=True,
    )
    height = models.PositiveIntegerField(
        editable=False,
        null=True,
        blank=True,
    )
    file_size_bytes = models.PositiveIntegerField(
        editable=False,
        default=0,
    )
    # url = models.URLField(max_length=2048)
    alt_text = models.CharField(max_length=240, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        indexes = [models.Index(fields=["product", "sort_order"])]


class ProductImageRendition(models.Model):
    class Kind(models.TextChoices):
        THUMBNAIL = "thumbnail", "Thumbnail"
        CARD = "card", "Card"
        DETAIL = "detail", "Detail"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_image = models.ForeignKey(
        "catalog.ProductImage",
        on_delete=models.CASCADE,
        related_name="renditions",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    image = models.ImageField(upload_to=product_image_rendition_upload_path, max_length=255)
    width = models.PositiveIntegerField(editable=False)
    height = models.PositiveIntegerField(editable=False)
    file_size_bytes = models.PositiveIntegerField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_image", "kind"],
                name="uq_product_image_rendition_kind",
            )
        ]


class ProductOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="options",
    )
    name = models.CharField(max_length=80)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "name"],
                name="uq_product_option_name",
            )
        ]


class ProductOptionValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    option = models.ForeignKey(
        "catalog.ProductOption",
        on_delete=models.CASCADE,
        related_name="values",
    )
    value = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["option", "value"],
                name="uq_option_value",
            )
        ]


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="variants",
    )
    sku = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    selling_price_cents = models.PositiveBigIntegerField()
    sale_price_cents = models.PositiveBigIntegerField(null=True, blank=True)
    sale_starts_at = models.DateTimeField(null=True, blank=True)
    sale_ends_at = models.DateTimeField(null=True, blank=True)
    last_sale_at = models.DateTimeField(null=True, blank=True)
    option_values = models.ManyToManyField(
        "catalog.ProductOptionValue",
        through="catalog.VariantOptionValue",
        related_name="variants",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_id", "sku"]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["sale_starts_at", "sale_ends_at"]),
        ]

    def clean(self):
        super().clean()
        if self.sale_ends_at and not self.sale_starts_at:
            raise ValidationError({"sale_starts_at": "A sale end requires a sale start."})
        if self.sale_starts_at and self.sale_ends_at and self.sale_ends_at <= self.sale_starts_at:
            raise ValidationError({"sale_ends_at": "Sale end must be after sale start."})

    @property
    def active_price_cents(self):
        now = timezone.now()
        sale_is_active = (
            self.sale_price_cents is not None
            and self.sale_starts_at is not None
            and self.sale_starts_at <= now
            and (self.sale_ends_at is None or now < self.sale_ends_at)
        )
        return self.sale_price_cents if sale_is_active else self.selling_price_cents

    def __str__(self):
        return self.sku


class VariantOptionValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="option_assignments",
    )
    option = models.ForeignKey("catalog.ProductOption", on_delete=models.PROTECT)
    value = models.ForeignKey("catalog.ProductOptionValue", on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "option"],
                name="uq_variant_option",
            ),
            models.UniqueConstraint(
                fields=["variant", "value"],
                name="uq_variant_option_value",
            ),
        ]

    def clean(self):
        super().clean()
        if self.value_id and self.option_id and self.value.option_id != self.option_id:
            raise ValidationError({"value": "The value does not belong to the selected option."})
        if self.variant_id and self.option_id and self.variant.product_id != self.option.product_id:
            raise ValidationError({"option": "The option does not belong to this product."})


class PriceHistory(models.Model):
    class Kind(models.TextChoices):
        STANDARD = "standard", "Standard"
        SALE = "sale", "Sale"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="price_history",
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    previous_cents = models.PositiveBigIntegerField(null=True, blank=True)
    new_cents = models.PositiveBigIntegerField(null=True, blank=True)
    sale_starts_at = models.DateTimeField(null=True, blank=True)
    sale_ends_at = models.DateTimeField(null=True, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="price_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [models.Index(fields=["variant", "changed_at"])]
