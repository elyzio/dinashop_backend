from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from catalog.models import Product, ProductCategory, ProductVariant
from custom.models import Category
from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError
from inventory.models import InventoryBalance, StockMovement, StockReservation
from order.models import Order, OrderLine


def _existing_matches(movement, line, data):
    return (
        movement.order_id == line.order_id
        and movement.reference == f"{line.order.number}:{line.id}"
        and movement.quantity_delta == line.quantity
        and movement.price_paid_cents == data["total_product_cost_cents"]
        and (movement.tax_cents or 0) == data.get("tax_cents", 0)
        and (movement.fees_cents or 0) == data.get("fees_cents", 0)
    )


def _receive_special_line_once(*, line, data, idempotency_key, actor, request=None):
    existing = StockMovement.objects.filter(idempotency_key=idempotency_key).select_related("order").first()
    if existing:
        if not _existing_matches(existing, line, data):
            raise ConflictError(
                "This idempotency key was used with different receiving data.",
                code="idempotency_conflict",
            )
        return line, existing, True

    with transaction.atomic():
        line = OrderLine.objects.select_for_update().select_related("order").get(pk=line.pk)
        order = Order.objects.select_for_update().get(pk=line.order_id)
        if line.kind != OrderLine.Kind.SPECIAL:
            raise ValidationError({"order_line": "Only special lines use this receiving command."})
        if order.special_status != Order.SpecialStatus.CONFIRMED:
            raise ConflictError(
                "The special order must be confirmed before receiving items.",
                code="invalid_transition",
            )
        if line.variant_id or hasattr(line, "reservation"):
            raise ConflictError("This special line was already received.", code="already_received")

        category = Category.objects.select_for_update().get(slug="special-order-stock")
        product = Product.objects.create(
            name=(line.product_name or line.description)[:180],
            description=f"Received for special order {order.number}: {line.description}",
            brand="",
            visibility=Product.Visibility.HIDDEN,
            has_variants=False,
        )
        ProductCategory.objects.create(product=product, category=category, is_primary=True)
        sku = f"{order.number}-{str(line.id).split('-')[0]}".upper()[:80]
        suffix = 1
        candidate = sku
        while ProductVariant.objects.filter(sku=candidate).exists():
            suffix += 1
            candidate = f"{sku[:74]}-{suffix}"
        variant = ProductVariant.objects.create(
            product=product,
            sku=candidate,
            selling_price_cents=line.unit_price_cents,
            is_active=True,
        )
        total_cost = (
            data["total_product_cost_cents"]
            + data.get("tax_cents", 0)
            + data.get("fees_cents", 0)
        )
        landed_cost = (total_cost + line.quantity // 2) // line.quantity
        InventoryBalance.objects.create(
            variant=variant,
            in_hand=line.quantity,
            promised=line.quantity,
            last_landed_cost_cents=landed_cost,
        )
        StockReservation.objects.create(
            order_line=line,
            variant=variant,
            quantity=line.quantity,
        )
        movement = StockMovement.objects.create(
            variant=variant,
            movement_type=StockMovement.Type.RECEIVED,
            quantity_delta=line.quantity,
            reference=f"{order.number}:{line.id}",
            order=order,
            price_paid_cents=data["total_product_cost_cents"],
            tax_cents=data.get("tax_cents", 0),
            fees_cents=data.get("fees_cents", 0),
            landed_cost_cents=landed_cost,
            note=data.get("note", "").strip(),
            idempotency_key=idempotency_key,
            recorded_by=actor,
        )
        line.variant = variant
        line.product_name = product.name
        line.sku = variant.sku
        line.landed_cost_cents = landed_cost
        line.save(update_fields=("variant", "product_name", "sku", "landed_cost_cents"))
        if not order.lines.filter(kind=OrderLine.Kind.SPECIAL, variant__isnull=True).exists():
            order.special_status = Order.SpecialStatus.ITEM_RECEIVED
        order.version += 1
        order.save(update_fields=("special_status", "version", "updated_at"))
        record_audit_event(
            actor=actor,
            action="order.special_item_received",
            entity_type="order.OrderLine",
            entity_id=line.id,
            after={
                "variant_id": str(variant.id),
                "landed_cost_cents": landed_cost,
                "quantity": line.quantity,
            },
            request=request,
        )
        return line, movement, False


def receive_special_line(*, line, data, idempotency_key, actor, request=None):
    try:
        return _receive_special_line_once(
            line=line,
            data=data,
            idempotency_key=idempotency_key,
            actor=actor,
            request=request,
        )
    except IntegrityError:
        existing = (
            StockMovement.objects.filter(idempotency_key=idempotency_key)
            .select_related("order")
            .first()
        )
        if existing:
            line = OrderLine.objects.select_related("order").get(pk=line.pk)
            if not _existing_matches(existing, line, data):
                raise ConflictError(
                    "This idempotency key was used with different receiving data.",
                    code="idempotency_conflict",
                )
            return line, existing, True
        raise
