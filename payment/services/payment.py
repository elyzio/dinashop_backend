from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from custom.models import DocumentSequence
from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError
from order.models import Order
from order.services.totals import balance_due_cents
from payment.models import Payment, TenderMethod


def _matches(payment, order, data):
    return (
        payment.order_id == order.id
        and payment.amount_cents == data["amount_cents"]
        and payment.method == data["method"]
        and payment.tendered_cents == data.get("tendered_cents")
        and payment.external_reference == data.get("external_reference", "").strip()
    )


def record_payment_locked(
    *, order, data, idempotency_key, actor, request=None, increment_version=True,
    received_by_name=None,
):
    existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if not _matches(existing, order, data):
            raise ConflictError(
                "This idempotency key was used with different payment data.",
                code="idempotency_conflict",
            )
        return existing, True
    if order.status in (Order.Status.CANCELLED, Order.Status.COMPLETED):
        raise ConflictError("Payments cannot be added to a terminal order.", code="terminal_order")
    balance = balance_due_cents(order)
    if data["amount_cents"] > balance:
        raise ConflictError(
            f"The payment exceeds the remaining balance of {balance} cents.",
            code="overpayment",
        )
    tendered = data.get("tendered_cents")
    if data["method"] == TenderMethod.CASH:
        if tendered is None or tendered < data["amount_cents"]:
            raise ValidationError({"tendered_cents": "Cash tendered must cover the payment."})
        change = tendered - data["amount_cents"]
    else:
        if tendered is not None:
            raise ValidationError({"tendered_cents": "Tendered cash is only valid for cash payments."})
        change = None
    payment = Payment.objects.create(
        order=order,
        amount_cents=data["amount_cents"],
        receipt_number=DocumentSequence.next_number(key="payment", prefix="PAY"),
        method=data["method"],
        received_by=actor,
        received_by_name=received_by_name or actor.get_full_name() or actor.email,
        tendered_cents=tendered,
        change_cents=change,
        external_reference=data.get("external_reference", "").strip(),
        idempotency_key=idempotency_key,
        occurred_at=data.get("occurred_at") or timezone.now(),
    )
    if increment_version:
        order.version += 1
        order.save(update_fields=("version", "updated_at"))
    record_audit_event(
        actor=actor, action="payment.recorded", entity_type="payment.Payment",
        entity_id=payment.id,
        after={"order_id": str(order.id), "amount_cents": payment.amount_cents, "method": payment.method},
        request=request,
    )
    return payment, False


def record_payment(*, order, order_version, data, idempotency_key, actor, request=None):
    existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if not _matches(existing, order, data):
            raise ConflictError(
                "This idempotency key was used with different payment data.",
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
            return record_payment_locked(
                order=order, data=data, idempotency_key=idempotency_key,
                actor=actor, request=request,
            )
    except IntegrityError:
        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            if not _matches(existing, order, data):
                raise ConflictError(
                    "This idempotency key was used with different payment data.",
                    code="idempotency_conflict",
                )
            return existing, True
        raise
