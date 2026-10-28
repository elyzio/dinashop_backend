from django.db import transaction

from catalog.models import ProductVariant
from custom.models import DocumentSequence
from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError


def allocate_internal_barcode() -> str:
    return DocumentSequence.next_number(key="barcode", prefix="DS", width=12)


@transaction.atomic
def generate_variant_barcode(*, variant, actor, request=None):
    variant = ProductVariant.objects.select_for_update().get(pk=variant.pk)
    if variant.barcode:
        raise ConflictError(
            "This variant already has a barcode.",
            code="barcode_exists",
        )
    variant.barcode = allocate_internal_barcode()
    variant.full_clean()
    variant.save(update_fields=("barcode", "updated_at"))
    record_audit_event(
        actor=actor,
        action="product_variant.barcode_generated",
        entity_type="catalog.ProductVariant",
        entity_id=variant.id,
        before={"barcode": None},
        after={"barcode": variant.barcode},
        request=request,
    )
    return variant


def record_barcode_change(*, variant, before, actor, request=None, generated=False):
    if before == variant.barcode:
        return
    record_audit_event(
        actor=actor,
        action=(
            "product_variant.barcode_generated"
            if generated
            else "product_variant.barcode_updated"
        ),
        entity_type="catalog.ProductVariant",
        entity_id=variant.id,
        before={"barcode": before},
        after={"barcode": variant.barcode},
        request=request,
    )
