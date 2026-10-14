import uuid

from django.db import migrations, models
from django.db.models import Q


WALK_IN_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


def seed_walk_in_customer(apps, schema_editor):
    Customer = apps.get_model("people", "Customer")
    Customer.objects.update_or_create(
        is_walk_in=True,
        defaults={
            "id": WALK_IN_ID,
            "name": "Walk-in Customer",
            "phone": "",
            "normalized_phone": "",
            "address": "",
            "note": "Protected customer for ordinary pickup sales.",
            "is_active": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("people", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="is_walk_in",
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(
                fields=("is_walk_in",),
                condition=Q(is_walk_in=True),
                name="uq_single_walk_in_customer",
            ),
        ),
        migrations.RunPython(seed_walk_in_customer, migrations.RunPython.noop),
    ]
