from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from custom.models import Category
from dina_shop.api.exceptions import ConflictError

from .audit import record_audit_event


PROTECTED_CATEGORY_SLUGS = {"special-order-stock", "special-return-stock"}


def _snapshot(category):
    return {
        "id": str(category.id),
        "name": category.name,
        "slug": category.slug,
        "parent_id": str(category.parent_id) if category.parent_id else None,
        "status": category.status,
        "sort_order": category.sort_order,
    }


def _model_validation(instance):
    try:
        instance.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict) from exc


def _unique_slug(name, *, exclude_id=None):
    base = slugify(name)[:130] or "category"
    candidate = base
    suffix = 2
    queryset = Category.objects.all()
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    while queryset.filter(slug=candidate).exists():
        candidate = f"{base[:130 - len(str(suffix))]}-{suffix}"
        suffix += 1
    return candidate


@transaction.atomic
def create_category(*, data, actor, request=None):
    category = Category(**data)
    category.slug = _unique_slug(category.name)
    _model_validation(category)
    category.save()
    record_audit_event(
        actor=actor,
        action="category.created",
        entity_type="custom.Category",
        entity_id=category.id,
        after=_snapshot(category),
        request=request,
    )
    return category


@transaction.atomic
def update_category(*, category, data, actor, request=None):
    category = Category.objects.select_for_update().get(pk=category.pk)
    before = _snapshot(category)
    for field, value in data.items():
        setattr(category, field, value)
    _model_validation(category)
    category.save()
    record_audit_event(
        actor=actor,
        action="category.updated",
        entity_type="custom.Category",
        entity_id=category.id,
        before=before,
        after=_snapshot(category),
        request=request,
    )
    return category


@transaction.atomic
def delete_category(*, category, actor, request=None):
    category = Category.objects.select_for_update().get(pk=category.pk)
    if category.slug in PROTECTED_CATEGORY_SLUGS:
        raise ConflictError("This category is required by stock workflows.", code="protected_category")
    if category.children.exists():
        raise ConflictError("Move or remove child categories first.", code="category_has_children")
    if category.product_links.exists():
        raise ConflictError("Remove this category from its products first.", code="category_in_use")
    before = _snapshot(category)
    category_id = category.id
    try:
        category.delete()
    except ProtectedError as exc:
        raise ConflictError("This category is still referenced.", code="category_in_use") from exc
    record_audit_event(
        actor=actor,
        action="category.deleted",
        entity_type="custom.Category",
        entity_id=category_id,
        before=before,
        request=request,
    )
