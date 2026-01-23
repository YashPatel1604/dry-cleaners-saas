from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0003_customer_phone_e164_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="customer",
            name="phone",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name="customer",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name="customer",
            name="notes",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["tenant", "phone"], name="customers_cus_tenant__phone_idx"),
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["tenant", "email"], name="customers_cus_tenant__email_idx"),
        ),
    ]
