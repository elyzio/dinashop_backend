from django.db import transaction
from rest_framework.exceptions import ValidationError

from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError
from people.models import Customer, Helper


def _snapshot(instance):
    fields = ("name", "phone", "normalized_phone", "note", "is_active")
    if isinstance(instance, Customer):
        fields += ("address", "is_walk_in")
    return {field: getattr(instance, field) for field in fields}


def _protect_walk_in(customer):
    if customer.is_walk_in:
        raise ConflictError(
            "The protected walk-in customer cannot be changed.",
            code="walk_in_protected",
        )


@transaction.atomic
def create_person(*, model, data, actor, request=None):
    instance = model(**data)
    instance.full_clean()
    instance.save()
    record_audit_event(
        actor=actor,
        action=f"{model._meta.model_name}.created",
        entity_type=instance._meta.label,
        entity_id=instance.id,
        after=_snapshot(instance),
        request=request,
    )
    return instance


@transaction.atomic
def update_person(*, instance, data, actor, request=None):
    instance = type(instance).objects.select_for_update().get(pk=instance.pk)
    if isinstance(instance, Customer):
        _protect_walk_in(instance)
    before = _snapshot(instance)
    for field, value in data.items():
        setattr(instance, field, value)
    instance.full_clean()
    instance.save()
    record_audit_event(
        actor=actor,
        action=f"{instance._meta.model_name}.updated",
        entity_type=instance._meta.label,
        entity_id=instance.id,
        before=before,
        after=_snapshot(instance),
        request=request,
    )
    return instance


@transaction.atomic
def set_person_active(*, instance, is_active, actor, request=None):
    instance = type(instance).objects.select_for_update().get(pk=instance.pk)
    if isinstance(instance, Customer):
        _protect_walk_in(instance)
    if instance.is_active == is_active:
        return instance
    before = _snapshot(instance)
    instance.is_active = is_active
    instance.save(update_fields=("is_active", "updated_at"))
    record_audit_event(
        actor=actor,
        action=f"{instance._meta.model_name}.{'reactivated' if is_active else 'deactivated'}",
        entity_type=instance._meta.label,
        entity_id=instance.id,
        before=before,
        after=_snapshot(instance),
        request=request,
    )
    return instance
