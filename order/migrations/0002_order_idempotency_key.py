from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("order", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="order",
            name="idempotency_key",
            field=models.UUIDField(blank=True, null=True, unique=True),
        ),
    ]
