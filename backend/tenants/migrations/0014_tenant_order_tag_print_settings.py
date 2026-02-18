from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0013_tenant_deactivated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="order_tag_copies",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="tenant",
            name="order_tag_label_size",
            field=models.CharField(
                choices=[("2x1", "2x1"), ("4x2", "4x2")],
                default="2x1",
                max_length=3,
            ),
        ),
    ]
