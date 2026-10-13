import uuid

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from custom.services.audit import record_audit_event
from inventory.models import InventoryBalance, StockMovement


def _balance_snapshot(balance):
    return {
        "variant_id": str(balance.variant_id),
        "in_hand": balance.in_hand,
        "promised": balance.promised,
        "available": balance.available,
        "last_landed_cost_cents": balance.last_landed_cost_cents,
    }


def receive_stock(*, data, idempotency_key, actor, request=None):
    existing = StockMovement.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing, existing.variant.inventory, True

    try:
        with transaction.atomic():
            variant = data["variant"]
            balance = InventoryBalance.objects.select_for_update().get(variant=variant)
            existing = StockMovement.objects.filter(
                idempotency_key=idempotency_key
            ).first()
            if existing:
                return existing, existing.variant.inventory, True
            before = _balance_snapshot(balance)
            quantity = data["quantity"]
            total_cost = (
                data["price_paid_cents"]
                + data.get("tax_cents", 0)
                + data.get("fees_cents", 0)
            )
            landed_cost = (total_cost + quantity // 2) // quantity
            balance.in_hand += quantity
            balance.last_landed_cost_cents = landed_cost
            balance.save(
                update_fields=("in_hand", "last_landed_cost_cents", "updated_at")
            )
            movement = StockMovement.objects.create(
                variant=variant,
                movement_type=StockMovement.Type.RECEIVED,
                quantity_delta=quantity,
                reference=f"RECEIVE-{str(idempotency_key).upper()}",
                order=data.get("order"),
                price_paid_cents=data["price_paid_cents"],
                tax_cents=data.get("tax_cents", 0),
                fees_cents=data.get("fees_cents", 0),
                landed_cost_cents=landed_cost,
                note=data.get("note", "").strip(),
                idempotency_key=idempotency_key,
                recorded_by=actor,
            )
            record_audit_event(
                actor=actor,
                action="stock.received",
                entity_type="inventory.InventoryBalance",
                entity_id=balance.id,
                before=before,
                after=_balance_snapshot(balance),
                request=request,
            )
    except IntegrityError:
        existing = StockMovement.objects.filter(idempotency_key=idempotency_key).first()
        if existing is None:
            raise
        return existing, existing.variant.inventory, True
    return movement, balance, False


@transaction.atomic
def adjust_stock(*, data, actor, request=None):
    variant = data["variant"]
    balance = InventoryBalance.objects.select_for_update().get(variant=variant)
    before = _balance_snapshot(balance)
    new_in_hand = balance.in_hand + data["quantity_delta"]
    if new_in_hand < 0:
        raise ValidationError(
            {"quantity_delta": "This adjustment would make in-hand stock negative."}
        )
    if new_in_hand < balance.promised:
        raise ValidationError(
            {"quantity_delta": "In-hand stock cannot be lower than promised stock."}
        )
    balance.in_hand = new_in_hand
    balance.save(update_fields=("in_hand", "updated_at"))
    movement_type = (
        StockMovement.Type.DAMAGED
        if data["reason"] == "damage"
        else StockMovement.Type.ADJUSTMENT
    )
    movement = StockMovement.objects.create(
        variant=variant,
        movement_type=movement_type,
        quantity_delta=data["quantity_delta"],
        reference=f"ADJUST-{uuid.uuid4().hex[:12].upper()}",
        note=(f"{data['reason']}: {data.get('note', '')}").strip(": "),
        recorded_by=actor,
    )
    record_audit_event(
        actor=actor,
        action="stock.adjusted",
        entity_type="inventory.InventoryBalance",
        entity_id=balance.id,
        before=before,
        after=_balance_snapshot(balance),
        request=request,
    )
    return movement, balance
