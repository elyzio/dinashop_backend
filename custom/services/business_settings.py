from django.db import transaction

from custom.models import BusinessSettings

from .audit import record_audit_event


@transaction.atomic
def save_business_settings(*, serializer, actor, request=None):
    instance = serializer.instance
    before = None
    if instance is not None:
        before = serializer.__class__(instance).data
    settings = serializer.save(key="default")
    after = serializer.__class__(settings).data
    record_audit_event(
        actor=actor,
        action="business_settings.updated" if before else "business_settings.created",
        entity_type="custom.BusinessSettings",
        entity_id=settings.id,
        before=before,
        after=after,
        request=request,
    )
    return settings
