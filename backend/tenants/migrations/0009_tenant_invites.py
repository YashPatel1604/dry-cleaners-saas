from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0008_tenant_membership_event"),
    ]

    operations = [
        migrations.CreateModel(
            name="TenantInvite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("role", models.CharField(choices=[("OWNER_ADMIN", "Owner admin"), ("OPERATOR", "Operator")], default="OPERATOR", max_length=20)),
                ("token_hash", models.CharField(max_length=64)),
                ("expires_at", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tenant_invites_created", to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invites", to="tenants.tenant")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["tenant", "created_at"], name="tenants_ten_tenant__8f60d0_idx"),
                    models.Index(fields=["tenant", "email"], name="tenants_ten_tenant__af8ec1_idx"),
                    models.Index(fields=["tenant", "token_hash"], name="tenants_ten_tenant__8d2507_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="TenantInviteEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("event_type", models.CharField(choices=[("CREATED", "Created"), ("RESENT", "Resent"), ("REVOKED", "Revoked"), ("ACCEPTED", "Accepted")], max_length=20)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tenant_invite_events", to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invite_events", to="tenants.tenant")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["tenant", "created_at"], name="tenants_ten_tenant__1e0877_idx"),
                    models.Index(fields=["tenant", "email"], name="tenants_ten_tenant__2665e9_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="tenantinvite",
            constraint=models.UniqueConstraint(condition=models.Q(("accepted_at__isnull", True), ("revoked_at__isnull", True)), fields=("tenant", "email"), name="uniq_active_invite_email_per_tenant"),
        ),
    ]
