from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError


class Tenant(models.Model):
    name = models.CharField(max_length=255)

    # Allow blank so callers don't have to think about it
    slug = models.SlugField(unique=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    default_turnaround_days = models.PositiveSmallIntegerField(default=2)
    default_ready_hour = models.PositiveSmallIntegerField(default=17)   # 0-23
    default_ready_minute = models.PositiveSmallIntegerField(default=0)
    require_paid_in_full_at_pickup = models.BooleanField(default=True)
    collects_tax = models.BooleanField(default=True)
    tax_rate_bps = models.PositiveIntegerField(default=800)

    def clean(self):
        if self.default_turnaround_days is not None and self.default_turnaround_days > 30:
            raise ValidationError(
                {"default_turnaround_days": "Must be <= 30."})

        if self.default_ready_hour is not None and self.default_ready_hour > 23:
            raise ValidationError({"default_ready_hour": "Must be 0-23."})

        if self.default_ready_minute is not None and self.default_ready_minute > 59:
            raise ValidationError({"default_ready_minute": "Must be 0-59."})
        if self.tax_rate_bps is not None and self.tax_rate_bps > 2000:
            raise ValidationError({"tax_rate_bps": "Must be <= 2000."})

    def save(self, *args, **kwargs):
        """
        Auto-generate a unique slug from name if not provided.
        Ensures uniqueness even if tenants share names.
        """
        if not self.slug:
            base = slugify(self.name) or "tenant"
            slug = base
            i = 2

            while Tenant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1

            self.slug = slug

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TenantMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        STAFF = "STAFF", "Staff"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_memberships_v2",
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STAFF
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "user")

    def __str__(self):
        return f"{self.user} -> {self.tenant} ({self.role})"


class TenantMembership(models.Model):
    class Role(models.TextChoices):
        OWNER_ADMIN = "OWNER_ADMIN", "Owner admin"
        OPERATOR = "OPERATOR", "Operator"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_memberships",
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.OPERATOR
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user"], name="uniq_tenant_membership"
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "user"]),
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.tenant} ({self.role})"


class TenantConfigEvent(models.Model):
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="config_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_config_events",
    )
    key = models.CharField(max_length=100)
    old_value = models.TextField()
    new_value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
        ]

    def __str__(self):
        return f"{self.tenant_id} {self.key}"
