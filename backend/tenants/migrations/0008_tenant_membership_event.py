from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0007_tenant_membership_and_config_event"),
    ]

    operations = [
        migrations.CreateModel(
            name="TenantMembershipEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=50)),
                ("before", models.JSONField(blank=True, null=True)),
                ("after", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tenant_membership_events", to=settings.AUTH_USER_MODEL)),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="tenants.tenantmembership")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="membership_events", to="tenants.tenant")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["tenant", "created_at"], name="tenants_ten_tenant__d0b0e8_idx"),
                ],
            },
        ),
    ]
