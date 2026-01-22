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
                ("action", models.CharField(choices=[("CREATED", "Created"), ("ROLE_CHANGED", "Role changed"), ("DEACTIVATED", "Deactivated"), ("REACTIVATED", "Reactivated")], max_length=20)),
                ("old_role", models.CharField(blank=True, max_length=20, null=True)),
                ("new_role", models.CharField(blank=True, max_length=20, null=True)),
                ("is_active_before", models.BooleanField(blank=True, null=True)),
                ("is_active_after", models.BooleanField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tenant_membership_events", to=settings.AUTH_USER_MODEL)),
                ("subject_user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tenant_membership_subject_events", to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="membership_events", to="tenants.tenant")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["tenant", "created_at"], name="tenants_ten_tenant__d0b0e8_idx"),
                ],
            },
        ),
    ]
