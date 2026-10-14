from django.db import IntegrityError, transaction
from django.db.models import Sum

from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError
from fulfillment.models import DeliveryJob
from payment.models import CodHandover


def _matches(handover, data):
    return (
        handover.helper_id == data["helper"].id
        and handover.order_id == data["order"].id
        and handover.amount_cents == data["amount_cents"]
    )


def record_cod_handover(*, data, idempotency_key, actor, request=None):
    existing = CodHandover.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if not _matches(existing, data):
            raise ConflictError(
                "This idempotency key was used with different handover data.",
                code="idempotency_conflict",
            )
        return existing, True
    try:
        with transaction.atomic():
            job = DeliveryJob.objects.select_for_update(of=("self",)).select_related("cod_payment").filter(
                order=data["order"],
                helper=data["helper"],
                status=DeliveryJob.Status.DELIVERED,
                cod_payment__isnull=False,
            ).first()
            if job is None:
                raise ConflictError(
                    "The helper and order do not identify a delivered COD job.",
                    code="cod_delivery_not_found",
                )
            handed = CodHandover.objects.select_for_update().filter(
                helper=data["helper"], order=data["order"],
            ).aggregate(total=Sum("amount_cents"))["total"] or 0
            held = job.cod_payment.amount_cents - handed
            if data["amount_cents"] > held:
                raise ConflictError(
                    f"The handover exceeds the held amount of {held} cents.",
                    code="cod_handover_exceeds_held",
                )
            handover = CodHandover.objects.create(
                helper=data["helper"],
                order=data["order"],
                amount_cents=data["amount_cents"],
                handed_over_at=data["handed_over_at"],
                recorded_by=actor,
                idempotency_key=idempotency_key,
            )
            record_audit_event(
                actor=actor, action="cod.handed_over", entity_type="payment.CodHandover",
                entity_id=handover.id,
                after={"amount_cents": handover.amount_cents, "held_cents": held - handover.amount_cents},
                request=request,
            )
            return handover, False
    except IntegrityError:
        existing = CodHandover.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            if not _matches(existing, data):
                raise ConflictError(
                    "This idempotency key was used with different handover data.",
                    code="idempotency_conflict",
                )
            return existing, True
        raise
