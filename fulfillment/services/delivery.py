from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError
from fulfillment.models import DeliveryJob
from order.models import Order
from order.services.totals import balance_due_cents
from order.services.workflow import _fulfill_locked, cancel_locked_order
from payment.models import TenderMethod
from payment.services.payment import record_payment_locked
from people.models import Helper


def _check_version(order, expected):
    if order.version != expected:
        raise ConflictError(
            f"The order changed after it was loaded. Current version: {order.version}.",
            code="stale_order",
        )


@transaction.atomic
def create_delivery_job(*, data, actor, request=None):
    order = Order.objects.select_for_update().get(pk=data["order"].pk)
    helper = Helper.objects.select_for_update().get(pk=data["helper"].pk)
    _check_version(order, data["order_version"])
    if not helper.is_active:
        raise ValidationError({"helper_id": "Choose an active helper."})
    if order.delivery_method != Order.DeliveryMethod.DELIVERY or order.status != Order.Status.CONFIRMED:
        raise ConflictError("This order is not eligible for delivery.", code="delivery_not_eligible")
    if order.special_status and order.special_status != Order.SpecialStatus.CUSTOMER_NOTIFIED:
        raise ConflictError("This special order is not ready for delivery.", code="delivery_not_eligible")
    if DeliveryJob.objects.filter(order=order).exists():
        raise ConflictError("This order already has a delivery job.", code="delivery_exists")
    now = timezone.now()
    job = DeliveryJob.objects.create(
        order=order,
        helper=helper,
        fee_cents=data.get("fee_cents", 0),
        fuel_cents=data.get("fuel_cents", 0),
        status_changed_at=now,
        created_by=actor,
        updated_by=actor,
    )
    order.version += 1
    order.save(update_fields=("version", "updated_at"))
    record_audit_event(
        actor=actor, action="delivery.assigned", entity_type="fulfillment.DeliveryJob",
        entity_id=job.id,
        after={"order_id": str(order.id), "helper_id": str(helper.id)}, request=request,
    )
    return job


@transaction.atomic
def start_delivery(*, job, order_version, actor, request=None):
    job = DeliveryJob.objects.select_for_update().select_related("order").get(pk=job.pk)
    order = Order.objects.select_for_update().get(pk=job.order_id)
    _check_version(order, order_version)
    if job.status != DeliveryJob.Status.ASSIGNED:
        raise ConflictError("Only assigned deliveries can start.", code="invalid_transition")
    job.status = DeliveryJob.Status.OUT_FOR_DELIVERY
    job.status_changed_at = timezone.now()
    job.updated_by = actor
    job.save(update_fields=("status", "status_changed_at", "updated_by", "updated_at"))
    order.version += 1
    order.save(update_fields=("version", "updated_at"))
    record_audit_event(
        actor=actor, action="delivery.started", entity_type="fulfillment.DeliveryJob",
        entity_id=job.id, request=request,
    )
    return job, False


@transaction.atomic
def deliver_order(*, job, order_version, idempotency_key, actor, request=None):
    job = (
        DeliveryJob.objects.select_for_update(of=("self",))
        .select_related("order", "helper", "cod_payment")
        .get(pk=job.pk)
    )
    if job.status == DeliveryJob.Status.DELIVERED:
        if job.cod_payment_id and job.cod_payment.idempotency_key != idempotency_key:
            raise ConflictError(
                "This delivery was completed with another idempotency key.",
                code="idempotency_conflict",
            )
        return job, True
    order = Order.objects.select_for_update().get(pk=job.order_id)
    _check_version(order, order_version)
    if job.status != DeliveryJob.Status.OUT_FOR_DELIVERY:
        raise ConflictError("Only an out-for-delivery job can be delivered.", code="invalid_transition")
    amount = balance_due_cents(order)
    _fulfill_locked(order, actor=actor, request=request)
    if order.cod and amount:
        payment, _ = record_payment_locked(
            order=order,
            data={
                "amount_cents": amount,
                "method": TenderMethod.CASH,
                "tendered_cents": amount,
                "external_reference": f"COD:{job.id}",
                "occurred_at": timezone.now(),
            },
            idempotency_key=idempotency_key,
            actor=actor,
            request=request,
            increment_version=False,
        )
        job.cod_payment = payment
    job.status = DeliveryJob.Status.DELIVERED
    job.failure_reason = ""
    job.status_changed_at = timezone.now()
    job.updated_by = actor
    job.save(update_fields=(
        "status", "failure_reason", "status_changed_at", "updated_by",
        "cod_payment", "updated_at",
    ))
    record_audit_event(
        actor=actor, action="delivery.delivered", entity_type="fulfillment.DeliveryJob",
        entity_id=job.id,
        after={"cod_payment_id": str(job.cod_payment_id) if job.cod_payment_id else None}, request=request,
    )
    return job, False


@transaction.atomic
def fail_delivery(*, job, order_version, failure_reason, actor, request=None):
    job = DeliveryJob.objects.select_for_update().select_related("order").get(pk=job.pk)
    order = Order.objects.select_for_update().get(pk=job.order_id)
    _check_version(order, order_version)
    if job.status != DeliveryJob.Status.OUT_FOR_DELIVERY:
        raise ConflictError("Only an out-for-delivery job can fail.", code="invalid_transition")
    job.status = DeliveryJob.Status.FAILED
    job.failure_reason = failure_reason.strip()
    job.status_changed_at = timezone.now()
    job.updated_by = actor
    job.save(update_fields=("status", "failure_reason", "status_changed_at", "updated_by", "updated_at"))
    cancel_locked_order(order, reason=job.failure_reason, actor=actor, request=request)
    record_audit_event(
        actor=actor, action="delivery.failed", entity_type="fulfillment.DeliveryJob",
        entity_id=job.id, after={"failure_reason": job.failure_reason}, request=request,
    )
    return job, False
