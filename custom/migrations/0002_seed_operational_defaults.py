from django.db import migrations


def seed_defaults(apps, schema_editor):
    BusinessSettings = apps.get_model("custom", "BusinessSettings")
    Category = apps.get_model("custom", "Category")
    DocumentSequence = apps.get_model("custom", "DocumentSequence")

    for key, prefix in (
        ("order", "ORD"),
        ("special_order", "SO"),
        ("payment", "PAY"),
        ("refund", "RF"),
    ):
        DocumentSequence.objects.update_or_create(
            key=key,
            defaults={"prefix": prefix},
        )

    for name, slug in (
        ("Special Order Stock", "special-order-stock"),
        ("Special Return Stock", "special-return-stock"),
    ):
        Category.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "status": "hidden", "sort_order": 900},
        )

    BusinessSettings.objects.get_or_create(
        key="default",
        defaults={
            "business_name": "ImportHub",
            "receipt_footer": "Thank you for your business.",
            "currency": "USD",
            "timezone": "UTC",
            "low_stock_threshold": 5,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("custom", "0001_initial")]

    operations = [migrations.RunPython(seed_defaults, migrations.RunPython.noop)]
