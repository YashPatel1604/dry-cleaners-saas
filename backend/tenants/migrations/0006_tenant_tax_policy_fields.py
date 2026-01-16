from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0005_tenant_require_paid_in_full_at_pickup"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="collects_tax",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="tenant",
            name="tax_rate_bps",
            field=models.PositiveIntegerField(default=800),
        ),
    ]
