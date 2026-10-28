from django.db import migrations


def seed_barcode_sequence(apps, schema_editor):
    DocumentSequence = apps.get_model("custom", "DocumentSequence")
    DocumentSequence.objects.update_or_create(
        key="barcode",
        defaults={"prefix": "DS"},
    )


class Migration(migrations.Migration):
    dependencies = [("custom", "0004_businesssettings_email_coordinates")]

    operations = [
        migrations.RunPython(seed_barcode_sequence, migrations.RunPython.noop)
    ]
