from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0006_tenant_tax_policy_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="TenantMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("OWNER_ADMIN", "Owner admin"), ("OPERATOR", "Operator")], default="OPERATOR", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="tenants.tenant")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tenant_memberships_v2", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["tenant", "user"], name="tenants_ten_tenant__25c0a8_idx"),
                    models.Index(fields=["tenant", "is_active"], name="tenants_ten_tenant__62f0f1_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="TenantConfigEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=100)),
                ("old_value", models.TextField()),
                ("new_value", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tenant_config_events", to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="config_events", to="tenants.tenant")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["tenant", "created_at"], name="tenants_ten_tenant__4cc1e2_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="tenantmembership",
            constraint=models.UniqueConstraint(fields=["tenant", "user"], name="uniq_tenant_membership"),
        ),
    ]
