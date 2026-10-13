from django.db.models import Count

from custom.models import Category


def category_queryset():
    return Category.objects.select_related("parent").annotate(
        child_count=Count("children", distinct=True),
        product_count=Count("product_links", distinct=True),
    )
