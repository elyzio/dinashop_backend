from django.utils.text import slugify

from catalog.models import Product


def generate_public_slug(name: str) -> str:
    """Return a collision-safe, URL-friendly slug for a newly created product."""
    base = slugify(name)[:180] or "product"
    candidate = base
    suffix = 2
    while Product.objects.filter(public_slug=candidate).exists():
        ending = f"-{suffix}"
        candidate = f"{base[: 200 - len(ending)]}{ending}"
        suffix += 1
    return candidate
