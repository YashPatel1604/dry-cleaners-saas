from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Tenant(models.Model):
    name = models.CharField(max_length=255)

    # Allow blank so callers don't have to think about it
    slug = models.SlugField(unique=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
        related_name="tenant_memberships",
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STAFF
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "user")

    def __str__(self):
        return f"{self.user} -> {self.tenant} ({self.role})"
