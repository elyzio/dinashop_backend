import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_product_public_slug")]

    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="barcode",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        regex="^[\\x20-\\x7E]+$",
                        message="Barcode may contain printable ASCII characters only.",
                    )
                ],
            ),
        )
    ]
