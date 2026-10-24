from django.db.models import Prefetch

from catalog.models import (
    Product,
    ProductCategory,
    ProductImage,
    ProductOption,
    ProductVariant,
    VariantOptionValue,
)


def variant_queryset():
    assignments = VariantOptionValue.objects.select_related("option", "value")
    return ProductVariant.objects.select_related("product", "inventory").prefetch_related(
        Prefetch("option_assignments", queryset=assignments)
    )


def product_queryset():
    options = ProductOption.objects.prefetch_related("values")
    return Product.objects.prefetch_related(
        Prefetch(
            "category_links",
            queryset=ProductCategory.objects.select_related("category"),
        ),
        Prefetch("images", queryset=ProductImage.objects.prefetch_related("renditions")),
        Prefetch("options", queryset=options),
        Prefetch("variants", queryset=variant_queryset()),
    )


def product_card_queryset():
    """Small, list-only graph. Full options are loaded only on product detail."""
    return Product.objects.prefetch_related(
        Prefetch(
            "category_links",
            queryset=ProductCategory.objects.select_related("category"),
        ),
        Prefetch(
            "images",
            queryset=ProductImage.objects.prefetch_related("renditions"),
        ),
        Prefetch(
            "variants",
            queryset=ProductVariant.objects.select_related("inventory"),
        ),
    )
