from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0012_password_reset_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="deactivated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
