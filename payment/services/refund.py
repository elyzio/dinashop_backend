import uuid

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from custom.models import DocumentSequence
from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError
from inventory.models import InventoryBalance, StockMovement
from order.models import Order, OrderLine
from order.services.totals import (
    cash_refunded_cents, order_total_cents, paid_cents, refunded_cents,
)
from order.services.workflow import _release_reservations
from payment.models import Refund, RefundLine


def _allocated_line_amounts(order, lines):
    gross = [
        line.unit_price_cents * line.quantity + (line.estimated_tax_cents or 0)
        for line in lines
    ]
    gross_total = sum(gross)
    total = order_total_cents(order)
    allocated = 0
    result = {}
    for index, line in enumerate(lines):
        amount = (
            total - allocated
            if index == len(lines) - 1
            else ((total * gross[index]) // gross_total if gross_total else 0)
        )
        allocated += amount
        result[line.id] = amount
    return result


def _line_refund_amount(line, allocated, quantity, already_returned):
    base, remainder = divmod(allocated, line.quantity)
    return sum(
        base + (1 if already_returned + offset < remainder else 0)
        for offset in range(quantity)
    )


def _refund_matches(refund, order, data):
    requested = {
        (item["order_line"].id, item["quantity"], item["disposition"])
        for item in data["lines"]
    }
    stored = {
        (item.order_line_id, item.quantity, item.disposition)
        for item in refund.lines.all()
    }
    return (
        refund.order_id == order.id
        and refund.method == data["method"]
        and refund.reason == data["reason"].strip()
        and requested == stored
    )


def _create_stock_effects(*, refund, entries, actor):
    variant_ids = sorted(
        {line.variant_id for line, _, _, _ in entries if line.variant_id},
        key=str,
    )
    balances = {
        item.variant_id: item
        for item in InventoryBalance.objects.select_for_update()
        .filter(variant_id__in=variant_ids)
        .order_by("variant_id")
    }
    for line, quantity, disposition, amount in entries:
        if not line.variant_id:
            raise ConflictError(
                "This returned line has no traceable inventory variant.",
                code="return_variant_missing",
            )
        balance = balances[line.variant_id]
        RefundLine.objects.create(
            refund=refund,
            order_line=line,
            quantity=quantity,
            disposition=disposition,
            amount_cents=amount,
            returned_variant_id=line.variant_id,
        )
        StockMovement.objects.create(
            variant_id=line.variant_id,
            movement_type=StockMovement.Type.REVERSAL,
            quantity_delta=quantity,
            reference=refund.number,
            order=refund.order,
            landed_cost_cents=line.landed_cost_cents or balance.last_landed_cost_cents,
            note=f"Refund {refund.number}",
            recorded_by=actor,
        )
        if disposition == RefundLine.Disposition.RESTOCK:
            balance.in_hand += quantity
            balance.save(update_fields=("in_hand", "updated_at"))
        else:
            StockMovement.objects.create(
                variant_id=line.variant_id,
                movement_type=StockMovement.Type.DAMAGED,
                quantity_delta=-quantity,
                reference=refund.number,
                order=refund.order,
                landed_cost_cents=line.landed_cost_cents or balance.last_landed_cost_cents,
                note=f"Damaged return for {refund.number}",
                recorded_by=actor,
            )


def create_refund(*, order, order_version, data, idempotency_key, actor, request=None):
    existing = Refund.objects.filter(idempotency_key=idempotency_key).prefetch_related("lines").first()
    if existing:
        if not _refund_matches(existing, order, data):
            raise ConflictError(
                "This idempotency key was used with different refund data.",
                code="idempotency_conflict",
            )
        return existing, True
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            if order.version != order_version:
                raise ConflictError(
                    f"The order changed after it was loaded. Current version: {order.version}.",
                    code="stale_order",
                )
            if not order.fulfilled_at:
                raise ConflictError("Only fulfilled orders can be refunded.", code="not_fulfilled")
            payment = data.get("payment")
            if payment and payment.order_id != order.id:
                raise ValidationError({"payment_id": "The payment must belong to this order."})
            lines = list(OrderLine.objects.select_for_update().filter(order=order).order_by("created_at"))
            line_map = {line.id: line for line in lines}
            allocations = _allocated_line_amounts(order, lines)
            entries = []
            seen = set()
            credit = 0
            for item in data["lines"]:
                line = line_map.get(item["order_line"].id)
                if line is None:
                    raise ValidationError({"lines": "Every line must belong to this order."})
                if line.id in seen:
                    raise ValidationError({"lines": "Each order line may appear only once."})
                seen.add(line.id)
                returned = RefundLine.objects.filter(order_line=line).aggregate(total=Sum("quantity"))["total"] or 0
                if returned + item["quantity"] > line.quantity:
                    raise ConflictError(
                        f"Only {line.quantity - returned} units remain refundable for line {line.id}.",
                        code="refund_limit_exceeded",
                    )
                amount = _line_refund_amount(
                    line, allocations[line.id], item["quantity"], returned,
                )
                credit += amount
                entries.append((line, item["quantity"], item["disposition"], amount))
            prior_credit = refunded_cents(order)
            prior_cash = cash_refunded_cents(order)
            net_paid = max(0, paid_cents(order) - prior_cash)
            new_net_total = max(0, order_total_cents(order) - prior_credit - credit)
            cash_refund = min(credit, max(0, net_paid - new_net_total))
            refund = Refund.objects.create(
                number=DocumentSequence.next_number(key="refund", prefix="RF"),
                order=order,
                payment=payment,
                credit_cents=credit,
                cash_refund_cents=cash_refund,
                method=data["method"],
                reason=data["reason"].strip(),
                processed_by=actor,
                processed_by_name=actor.get_full_name() or actor.email,
                idempotency_key=idempotency_key,
            )
            _create_stock_effects(refund=refund, entries=entries, actor=actor)
            order.version += 1
            order.save(update_fields=("version", "updated_at"))
            record_audit_event(
                actor=actor, action="refund.created", entity_type="payment.Refund",
                entity_id=refund.id,
                after={"order_id": str(order.id), "credit_cents": credit, "cash_refund_cents": cash_refund},
                request=request,
            )
            return refund, False
    except IntegrityError:
        existing = Refund.objects.filter(idempotency_key=idempotency_key).prefetch_related("lines").first()
        if existing:
            if not _refund_matches(existing, order, data):
                raise ConflictError(
                    "This idempotency key was used with different refund data.",
                    code="idempotency_conflict",
                )
            return existing, True
        raise


@transaction.atomic
def decline_special_order(*, order, data, actor, request=None):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.version != data["version"]:
        raise ConflictError(
            f"The order changed after it was loaded. Current version: {order.version}.",
            code="stale_order",
        )
    if order.special_status != Order.SpecialStatus.FINAL_PRICE_SET:
        raise ConflictError("Only a final-priced special order can be declined.", code="invalid_transition")
    estimate = max(0, sum(
        line.unit_price_cents * line.quantity + (line.estimated_tax_cents or 0)
        for line in order.lines.all()
    ) - order.discount_cents)
    if order.final_price_cents is None or order.final_price_cents <= estimate:
        raise ConflictError("Decline is only available when the final price increased.", code="decline_not_available")
    paid = max(0, paid_cents(order) - cash_refunded_cents(order))
    if paid:
        Refund.objects.create(
            number=DocumentSequence.next_number(key="refund", prefix="RF"),
            order=order,
            credit_cents=order_total_cents(order),
            cash_refund_cents=min(paid, order_total_cents(order)),
            method=data["method"],
            reason=data.get("reason", "Customer declined final price.").strip(),
            processed_by=actor,
            processed_by_name=actor.get_full_name() or actor.email,
            idempotency_key=uuid.uuid4(),
        )
    _release_reservations(order)
    order.status = Order.Status.CANCELLED
    order.special_status = Order.SpecialStatus.DECLINED
    order.cancelled_at = timezone.now()
    order.cancellation_reason = data.get("reason", "Customer declined final price.").strip()
    order.version += 1
    order.save(update_fields=(
        "status", "special_status", "cancelled_at", "cancellation_reason",
        "version", "updated_at",
    ))
    record_audit_event(
        actor=actor, action="order.special_declined", entity_type="order.Order",
        entity_id=order.id, after={"cash_refund_cents": paid}, request=request,
    )
    return order
