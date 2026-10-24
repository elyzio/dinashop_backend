# Generated manually for a deterministic backfill of public product URLs.

from django.db import migrations, models
from django.utils.text import slugify


def populate_public_slugs(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    used = set()
    for product in Product.objects.order_by("created_at", "id").iterator():
        base = slugify(product.name)[:180] or "product"
        candidate = base
        suffix = 2
        while candidate in used:
            ending = f"-{suffix}"
            candidate = f"{base[: 200 - len(ending)]}{ending}"
            suffix += 1
        used.add(candidate)
        product.public_slug = candidate
        product.save(update_fields=["public_slug"])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0003_productimagerendition")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="public_slug",
            # Avoid SlugField's automatic pattern index while values are
            # temporarily nullable. The final operation creates its one
            # unique slug index after the deterministic backfill.
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.RunPython(populate_public_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="product",
            name="public_slug",
            field=models.SlugField(editable=False, max_length=200, unique=True),
        ),
    ]
