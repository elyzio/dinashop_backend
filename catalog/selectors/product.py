from django.db.models import Prefetch

from catalog.models import (
    Product,
    ProductCategory,
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
        "images",
        Prefetch("options", queryset=options),
        Prefetch("variants", queryset=variant_queryset()),
    )
