import uuid

from custom.models import AuditEvent


def _request_id(request):
    if request is None:
        return None
    value = request.headers.get("X-Request-ID")
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError):
        return None


def record_audit_event(
    *, actor, action, entity_type, entity_id, before=None, after=None, request=None
):
    forwarded_for = request.headers.get("X-Forwarded-For", "") if request else ""
    ip_address = (
        forwarded_for.split(",", 1)[0].strip()
        if forwarded_for
        else (request.META.get("REMOTE_ADDR") if request else None)
    )
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before=before or {},
        after=after or {},
        request_id=_request_id(request),
        ip_address=ip_address,
    )
