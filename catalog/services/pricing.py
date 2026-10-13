from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from catalog.models import PriceHistory, ProductVariant
from custom.services.audit import record_audit_event


def _validate_variant(variant):
    try:
        variant.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict) from exc


def apply_pricing_changes(*, variant, changes, actor):
    previous_standard = variant.selling_price_cents
    previous_sale = variant.sale_price_cents
    previous_start = variant.sale_starts_at
    previous_end = variant.sale_ends_at

    for field, value in changes.items():
        setattr(variant, field, value)
    _validate_variant(variant)
    variant.save(
        update_fields=tuple(changes.keys()) + ("updated_at",)
    )

    if variant.selling_price_cents != previous_standard:
        PriceHistory.objects.create(
            variant=variant,
            kind=PriceHistory.Kind.STANDARD,
            previous_cents=previous_standard,
            new_cents=variant.selling_price_cents,
            changed_by=actor,
        )
    sale_changed = (
        variant.sale_price_cents != previous_sale
        or variant.sale_starts_at != previous_start
        or variant.sale_ends_at != previous_end
    )
    if sale_changed:
        PriceHistory.objects.create(
            variant=variant,
            kind=PriceHistory.Kind.SALE,
            previous_cents=previous_sale,
            new_cents=variant.sale_price_cents,
            sale_starts_at=variant.sale_starts_at,
            sale_ends_at=variant.sale_ends_at,
            changed_by=actor,
        )


@transaction.atomic
def update_variant_pricing(*, variant, changes, actor, request=None):
    variant = ProductVariant.objects.select_for_update().get(pk=variant.pk)
    before = {
        "selling_price_cents": variant.selling_price_cents,
        "sale_price_cents": variant.sale_price_cents,
        "sale_starts_at": variant.sale_starts_at.isoformat() if variant.sale_starts_at else None,
        "sale_ends_at": variant.sale_ends_at.isoformat() if variant.sale_ends_at else None,
    }
    apply_pricing_changes(variant=variant, changes=changes, actor=actor)
    after = {
        "selling_price_cents": variant.selling_price_cents,
        "sale_price_cents": variant.sale_price_cents,
        "sale_starts_at": variant.sale_starts_at.isoformat() if variant.sale_starts_at else None,
        "sale_ends_at": variant.sale_ends_at.isoformat() if variant.sale_ends_at else None,
    }
    record_audit_event(
        actor=actor,
        action="product_variant.pricing_updated",
        entity_type="catalog.ProductVariant",
        entity_id=variant.id,
        before=before,
        after=after,
        request=request,
    )
    return variant
