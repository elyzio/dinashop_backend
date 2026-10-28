from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from catalog.models import (
    Product,
    ProductCategory,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    VariantOptionValue,
)
from custom.models import Category
from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError
from inventory.models import InventoryBalance

from .barcode import allocate_internal_barcode, record_barcode_change
from .public_slug import generate_public_slug

from .pricing import apply_pricing_changes


def _product_snapshot(product):
    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description,
        "brand": product.brand,
        "visibility": product.visibility,
        "has_variants": product.has_variants,
    }


def _load_categories(category_ids):
    categories = list(Category.objects.filter(id__in=category_ids))
    if len(categories) != len(set(category_ids)):
        raise ValidationError({"category_ids": "One or more categories do not exist."})
    return {category.id: category for category in categories}


def _normalise_definitions(definitions):
    result = []
    seen_options = set()
    for index, definition in enumerate(definitions):
        name = definition["name"].strip()
        key = name.casefold()
        if not name or key in seen_options:
            raise ValidationError(
                {"option_definitions": f"Option names must be non-empty and unique (item {index})."}
            )
        seen_options.add(key)
        values = []
        seen_values = set()
        for raw_value in definition["values"]:
            value = raw_value.strip()
            value_key = value.casefold()
            if not value or value_key in seen_values:
                raise ValidationError(
                    {"option_definitions": f"Values for {name} must be non-empty and unique."}
                )
            seen_values.add(value_key)
            values.append(value)
        result.append({"name": name, "values": values})
    return result


def _normalise_variants(variants, option_definitions):
    option_names = {item["name"].casefold(): item for item in option_definitions}
    skus = set()
    result = []
    barcodes = set()
    for index, data in enumerate(variants):
        item = dict(data)
        sku = item["sku"].strip().upper()
        if not sku or sku.casefold() in skus:
            raise ValidationError({"variants": f"Every variant requires a unique SKU (item {index})."})
        skus.add(sku.casefold())
        barcode = item.get("barcode")
        if isinstance(barcode, str):
            barcode = barcode.strip() or None
            item["barcode"] = barcode
        if barcode:
            if barcode in barcodes:
                raise ValidationError(
                    {"variants": f"Barcode {barcode} is repeated in the variant grid."}
                )
            barcodes.add(barcode)
        raw_options = item.get("options", {})
        supplied_names = {name.strip().casefold() for name in raw_options}
        if supplied_names != set(option_names):
            raise ValidationError(
                {"variants": f"Variant {sku} must select one value for every option."}
            )
        options = {}
        for raw_name, raw_value in raw_options.items():
            definition = option_names[raw_name.strip().casefold()]
            value = raw_value.strip()
            allowed = {candidate.casefold(): candidate for candidate in definition["values"]}
            if value.casefold() not in allowed:
                raise ValidationError(
                    {"variants": f"{value!r} is not valid for option {definition['name']}."}
                )
            options[definition["name"]] = allowed[value.casefold()]
        item["sku"] = sku
        item["options"] = options
        result.append(item)
    return result


def _validate_variant_model(variant):
    try:
        variant.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict) from exc


def _ensure_skus_available(variants, *, product=None):
    for item in variants:
        queryset = ProductVariant.objects.filter(sku__iexact=item["sku"])
        variant_id = item.get("id")
        if variant_id:
            queryset = queryset.exclude(pk=variant_id)
        if product is not None:
            queryset = queryset.exclude(product=product, pk=variant_id)
        if queryset.exists():
            raise ValidationError({"variants": f"SKU {item['sku']} is already in use."})


def _ensure_barcodes_available(variants):
    for item in variants:
        barcode = item.get("barcode")
        if not barcode:
            continue
        queryset = ProductVariant.objects.filter(barcode=barcode)
        if item.get("id"):
            queryset = queryset.exclude(pk=item["id"])
        if queryset.exists():
            raise ValidationError(
                {"variants": f"Barcode {barcode} is already assigned to another variant."}
            )


def _create_option_tree(product, definitions):
    lookup = {}
    for option_index, definition in enumerate(definitions):
        option = ProductOption.objects.create(
            product=product,
            name=definition["name"],
            sort_order=option_index,
        )
        values = {}
        for value_index, value_name in enumerate(definition["values"]):
            value = ProductOptionValue.objects.create(
                option=option,
                value=value_name,
                sort_order=value_index,
            )
            values[value_name.casefold()] = value
        lookup[definition["name"].casefold()] = (option, values)
    return lookup


def _assign_options(variant, options, option_lookup):
    VariantOptionValue.objects.filter(variant=variant).delete()
    for option_name, value_name in options.items():
        option, values = option_lookup[option_name.casefold()]
        VariantOptionValue.objects.create(
            variant=variant,
            option=option,
            value=values[value_name.casefold()],
        )


@transaction.atomic
def create_product(*, data, actor, request=None):
    data = dict(data)
    category_ids = data.pop("category_ids")
    primary_category_id = data.pop("primary_category_id")
    definitions = _normalise_definitions(data.pop("option_definitions", []))
    variants = _normalise_variants(data.pop("variants"), definitions)
    _load_categories(category_ids)
    _ensure_skus_available(variants)
    _ensure_barcodes_available(variants)

    product = Product.objects.create(
        **data,
        public_slug=generate_public_slug(data["name"]),
        has_variants=bool(definitions) or len(variants) > 1,
    )
    for index, category_id in enumerate(category_ids):
        ProductCategory.objects.create(
            product=product,
            category_id=category_id,
            is_primary=category_id == primary_category_id,
            sort_order=index,
        )
    option_lookup = _create_option_tree(product, definitions)
    for item in variants:
        item = dict(item)
        options = item.pop("options")
        item.pop("id", None)
        generate_barcode = item.pop("generate_barcode", False)
        if generate_barcode:
            item["barcode"] = allocate_internal_barcode()
        variant = ProductVariant(product=product, **item)
        _validate_variant_model(variant)
        variant.save()
        InventoryBalance.objects.create(variant=variant)
        _assign_options(variant, options, option_lookup)
        if variant.barcode:
            record_barcode_change(
                variant=variant,
                before=None,
                actor=actor,
                request=request,
                generated=generate_barcode,
            )

    record_audit_event(
        actor=actor,
        action="product.created",
        entity_type="catalog.Product",
        entity_id=product.id,
        after=_product_snapshot(product),
        request=request,
    )
    return product


@transaction.atomic
def update_product(*, product, data, actor, request=None):
    product = Product.objects.select_for_update().get(pk=product.pk)
    before = _product_snapshot(product)
    data = dict(data)
    category_ids = data.pop("category_ids", None)
    primary_category_id = data.pop("primary_category_id", None)
    for field, value in data.items():
        setattr(product, field, value.strip() if isinstance(value, str) else value)
    product.save()

    if category_ids is not None or primary_category_id is not None:
        existing_links = list(product.category_links.all())
        if category_ids is None:
            category_ids = [link.category_id for link in existing_links]
        if primary_category_id is None:
            primary = next((link.category_id for link in existing_links if link.is_primary), None)
            primary_category_id = primary
        if primary_category_id not in category_ids:
            raise ValidationError(
                {"primary_category_id": "The primary category must be selected."}
            )
        _load_categories(category_ids)
        product.category_links.all().delete()
        for index, category_id in enumerate(category_ids):
            ProductCategory.objects.create(
                product=product,
                category_id=category_id,
                is_primary=category_id == primary_category_id,
                sort_order=index,
            )

    record_audit_event(
        actor=actor,
        action="product.updated",
        entity_type="catalog.Product",
        entity_id=product.id,
        before=before,
        after=_product_snapshot(product),
        request=request,
    )
    return product


def _variant_is_referenced(variant):
    inventory = getattr(variant, "inventory", None)
    return bool(
        (inventory and (inventory.in_hand or inventory.promised))
        or variant.reservations.exists()
        or variant.stock_movements.exists()
        or variant.price_history.exists()
        or variant.order_lines.exists()
    )


def _variant_mode_is_locked(variants):
    return any(_variant_is_referenced(variant) for variant in variants)


@transaction.atomic
def replace_variant_grid(*, product, data, actor, request=None):
    product = Product.objects.select_for_update().get(pk=product.pk)
    definitions = _normalise_definitions(data.get("option_definitions", []))
    variants = _normalise_variants(data["variants"], definitions)
    _ensure_skus_available(variants, product=product)
    _ensure_barcodes_available(variants)

    existing_options = list(
        ProductOption.objects.select_for_update().filter(product=product).prefetch_related("values")
    )
    option_lookup = {}
    requested_option_ids = set()
    for option_index, definition in enumerate(definitions):
        option = next(
            (item for item in existing_options if item.name.casefold() == definition["name"].casefold()),
            None,
        )
        if option is None:
            option = ProductOption.objects.create(
                product=product,
                name=definition["name"],
                sort_order=option_index,
            )
            existing_values = []
        else:
            option.name = definition["name"]
            option.sort_order = option_index
            option.save(update_fields=("name", "sort_order"))
            existing_values = list(option.values.all())
        requested_option_ids.add(option.id)
        values = {}
        requested_value_ids = set()
        for value_index, value_name in enumerate(definition["values"]):
            value = next(
                (item for item in existing_values if item.value.casefold() == value_name.casefold()),
                None,
            )
            if value is None:
                value = ProductOptionValue.objects.create(
                    option=option,
                    value=value_name,
                    sort_order=value_index,
                )
            else:
                value.value = value_name
                value.sort_order = value_index
                value.save(update_fields=("value", "sort_order"))
            requested_value_ids.add(value.id)
            values[value_name.casefold()] = value
        ProductOptionValue.objects.filter(option=option).exclude(
            id__in=requested_value_ids
        ).filter(variants__isnull=True).delete()
        option_lookup[definition["name"].casefold()] = (option, values)

    existing_variants = {
        item.id: item
        for item in ProductVariant.objects.select_for_update()
        .filter(product=product)
    }
    requested_has_variants = bool(definitions) or len(variants) > 1
    if product.has_variants != requested_has_variants and _variant_mode_is_locked(
        existing_variants.values()
    ):
        raise ConflictError(
            "Product mode cannot be changed after a variant has stock or operational history.",
            code="variant_mode_locked",
        )
    requested_ids = set()
    for item in variants:
        item = dict(item)
        options = item.pop("options")
        variant_id = item.pop("id", None)
        generate_barcode = item.pop("generate_barcode", False)
        if variant_id:
            variant = existing_variants.get(variant_id)
            if variant is None:
                raise ValidationError({"variants": f"Variant {variant_id} does not belong to this product."})
            requested_ids.add(variant.id)
            previous_barcode = variant.barcode
            if generate_barcode:
                if previous_barcode:
                    raise ConflictError(
                        "This variant already has a barcode.",
                        code="barcode_exists",
                    )
                item["barcode"] = allocate_internal_barcode()
            pricing_fields = {
                key: item.pop(key)
                for key in (
                    "selling_price_cents",
                    "sale_price_cents",
                    "sale_starts_at",
                    "sale_ends_at",
                )
                if key in item
            }
            for field, value in item.items():
                setattr(variant, field, value)
            _validate_variant_model(variant)
            variant.save()
            apply_pricing_changes(variant=variant, changes=pricing_fields, actor=actor)
            record_barcode_change(
                variant=variant,
                before=previous_barcode,
                actor=actor,
                request=request,
                generated=generate_barcode,
            )
        else:
            if generate_barcode:
                item["barcode"] = allocate_internal_barcode()
            variant = ProductVariant(product=product, **item)
            _validate_variant_model(variant)
            variant.save()
            InventoryBalance.objects.create(variant=variant)
            requested_ids.add(variant.id)
            if variant.barcode:
                record_barcode_change(
                    variant=variant,
                    before=None,
                    actor=actor,
                    request=request,
                    generated=generate_barcode,
                )
        _assign_options(variant, options, option_lookup)

    for variant_id, variant in existing_variants.items():
        if variant_id in requested_ids:
            continue
        if _variant_is_referenced(variant):
            if variant.is_active:
                variant.is_active = False
                variant.save(update_fields=("is_active", "updated_at"))
        else:
            variant.inventory.delete()
            variant.delete()

    for option in existing_options:
        if option.id not in requested_option_ids and not option.variantoptionvalue_set.exists():
            option.delete()

    product.has_variants = requested_has_variants
    product.save(update_fields=("has_variants", "updated_at"))
    record_audit_event(
        actor=actor,
        action="product.variant_grid_replaced",
        entity_type="catalog.Product",
        entity_id=product.id,
        after={"variant_count": len(variants), "option_count": len(definitions)},
        request=request,
    )
    return product


@transaction.atomic
def update_product_visibility(*, product, visibility, actor, request=None):
    product = Product.objects.select_for_update().get(pk=product.pk)
    if visibility == Product.Visibility.HIDDEN:
        promised = InventoryBalance.objects.filter(
            variant__product=product,
            promised__gt=0,
        ).exists()
        if promised:
            raise ConflictError(
                "This product cannot be hidden while stock is promised.",
                code="promised_stock_exists",
            )
    before = product.visibility
    product.visibility = visibility
    product.save(update_fields=("visibility", "updated_at"))
    record_audit_event(
        actor=actor,
        action="product.visibility_updated",
        entity_type="catalog.Product",
        entity_id=product.id,
        before={"visibility": before},
        after={"visibility": visibility},
        request=request,
    )
    return product
