from collections import defaultdict

from django.db.models import Case, F, IntegerField, Min, Prefetch, Q, When
from django.utils import timezone
from rest_framework.exceptions import NotFound

from catalog.models import (
    Product,
    ProductCategory,
    ProductImage,
    ProductOption,
    ProductVariant,
    VariantOptionValue,
)
from custom.models import Category


PUBLIC_EXCLUDED_CATEGORY_SLUGS = {
    "special-order-stock",
    "special-return-stock",
}


def _public_product_ids():
    """Base public product IDs before prefetching the public read graph."""
    return (
        Product.objects.filter(
            visibility=Product.Visibility.ACTIVE,
            variants__is_active=True,
            category_links__category__status=Category.Status.ACTIVE,
        )
        .exclude(category_links__category__slug__in=PUBLIC_EXCLUDED_CATEGORY_SLUGS)
        .values("id")
        .distinct()
    )


def _category_graph():
    categories = list(
        Category.objects.filter(status=Category.Status.ACTIVE)
        .exclude(slug__in=PUBLIC_EXCLUDED_CATEGORY_SLUGS)
        .order_by("sort_order", "name")
    )
    children = defaultdict(list)
    for category in categories:
        children[category.parent_id].append(category)
    return categories, children


def _descendant_ids(category, children):
    result = set()
    pending = [category]
    while pending:
        item = pending.pop()
        if item.id in result:
            continue
        result.add(item.id)
        pending.extend(children.get(item.id, []))
    return result


def get_public_category(slug: str):
    category = (
        Category.objects.filter(status=Category.Status.ACTIVE)
        .exclude(slug__in=PUBLIC_EXCLUDED_CATEGORY_SLUGS)
        .filter(slug=slug)
        .first()
    )
    if category is None:
        raise NotFound("The requested public category does not exist.")
    _, children = _category_graph()
    return category, _descendant_ids(category, children)


def public_product_queryset(*, category_slug: str | None = None):
    """Optimized public-only product graph without operational fields."""
    assignments = VariantOptionValue.objects.select_related("option", "value")
    variants = (
        ProductVariant.objects.filter(is_active=True)
        .select_related("inventory")
        .prefetch_related(Prefetch("option_assignments", queryset=assignments))
    )
    public_links = (
        ProductCategory.objects.select_related("category")
        .filter(category__status=Category.Status.ACTIVE)
        .exclude(category__slug__in=PUBLIC_EXCLUDED_CATEGORY_SLUGS)
        .order_by("sort_order", "category__sort_order", "category__name")
    )
    options = ProductOption.objects.prefetch_related("values")
    queryset = (
        Product.objects.filter(id__in=_public_product_ids())
        .prefetch_related(
            Prefetch("category_links", queryset=public_links, to_attr="public_category_links"),
            Prefetch("images", queryset=ProductImage.objects.prefetch_related("renditions")),
            Prefetch("options", queryset=options),
            Prefetch("variants", queryset=variants, to_attr="public_variants"),
        )
        .distinct()
    )

    if category_slug:
        _, category_ids = get_public_category(category_slug)
        queryset = queryset.filter(category_links__category_id__in=category_ids).distinct()

    now = timezone.now()
    current_price = Case(
        When(
            Q(variants__is_active=True)
            & Q(variants__sale_price_cents__isnull=False)
            & Q(variants__sale_starts_at__lte=now)
            & (Q(variants__sale_ends_at__isnull=True) | Q(variants__sale_ends_at__gt=now)),
            then=F("variants__sale_price_cents"),
        ),
        default=F("variants__selling_price_cents"),
        output_field=IntegerField(),
    )
    return queryset.annotate(public_from_price_cents=Min(current_price))


def public_sitemap_products():
    """Small public-product projection for the dynamic XML sitemap."""
    return (
        Product.objects.filter(id__in=_public_product_ids())
        .only("public_slug", "updated_at")
        .order_by("public_slug")
    )


def public_category_records():
    """Return active category metadata and counts including active descendants."""
    categories, children = _category_graph()
    category_by_id = {category.id: category for category in categories}
    direct_product_ids = defaultdict(set)
    pairs = ProductCategory.objects.filter(
        product_id__in=_public_product_ids(),
        category_id__in=category_by_id,
    ).values_list("product_id", "category_id")
    for product_id, category_id in pairs:
        direct_product_ids[category_id].add(product_id)

    descendant_products = {}

    def products_for(category):
        if category.id in descendant_products:
            return descendant_products[category.id]
        product_ids = set(direct_product_ids[category.id])
        for child in children.get(category.id, []):
            product_ids.update(products_for(child))
        descendant_products[category.id] = product_ids
        return product_ids

    records = []
    for category in categories:
        count = len(products_for(category))
        if count:
            records.append(
                {
                    "name": category.name,
                    "slug": category.slug,
                    "parent_slug": (
                        category_by_id[category.parent_id].slug
                        if category.parent_id in category_by_id
                        else None
                    ),
                    "sort_order": category.sort_order,
                    "product_count": count,
                }
            )
    return records
