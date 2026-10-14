import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fulfillment", "0001_initial"),
        ("payment", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="deliveryjob",
            name="cod_payment",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cod_delivery_job",
                to="payment.payment",
            ),
        ),
    ]
