from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils import timezone
import hashlib


class Tenant(models.Model):
    class OrderTagLabelSize(models.TextChoices):
        TWO_BY_ONE = "2x1", "2x1"
        FOUR_BY_TWO = "4x2", "4x2"

    name = models.CharField(max_length=255)

    # Allow blank so callers don't have to think about it
    slug = models.SlugField(unique=True, blank=True)

    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    default_turnaround_days = models.PositiveSmallIntegerField(default=2)
    default_ready_hour = models.PositiveSmallIntegerField(default=17)   # 0-23
    default_ready_minute = models.PositiveSmallIntegerField(default=0)
    require_paid_in_full_at_pickup = models.BooleanField(default=True)
    collects_tax = models.BooleanField(default=True)
    tax_rate_bps = models.PositiveIntegerField(default=800)
    order_tag_label_size = models.CharField(
        max_length=3,
        choices=OrderTagLabelSize.choices,
        default=OrderTagLabelSize.TWO_BY_ONE,
    )
    order_tag_copies = models.PositiveSmallIntegerField(default=1)

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
        if self.order_tag_copies is not None and (
            self.order_tag_copies < 1 or self.order_tag_copies > 20
        ):
            raise ValidationError({"order_tag_copies": "Must be between 1 and 20."})

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


class TenantMembershipEvent(models.Model):
    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        ROLE_CHANGED = "ROLE_CHANGED", "Role changed"
        DEACTIVATED = "DEACTIVATED", "Deactivated"
        REACTIVATED = "REACTIVATED", "Reactivated"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="membership_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_membership_events",
    )
    subject_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_membership_subject_events",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    old_role = models.CharField(max_length=20, null=True, blank=True)
    new_role = models.CharField(max_length=20, null=True, blank=True)
    is_active_before = models.BooleanField(null=True, blank=True)
    is_active_after = models.BooleanField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
        ]

    def __str__(self):
        return f"{self.tenant_id} {self.action}"


class TenantInvite(models.Model):
    class Role(models.TextChoices):
        OWNER_ADMIN = "OWNER_ADMIN", "Owner admin"
        OPERATOR = "OPERATOR", "Operator"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="invites"
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.OPERATOR
    )
    token_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_invites_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "email"]),
            models.Index(fields=["tenant", "token_hash"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "email"],
                condition=models.Q(accepted_at__isnull=True, revoked_at__isnull=True),
                name="uniq_active_invite_email_per_tenant",
            )
        ]

    @property
    def is_active(self) -> bool:
        if self.accepted_at or self.revoked_at:
            return False
        return self.expires_at > timezone.now()

    def mark_accepted(self):
        self.accepted_at = timezone.now()
        self.save(update_fields=["accepted_at"])

    def mark_revoked(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def __str__(self):
        return f"{self.tenant_id} {self.email} {self.role}"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "expires_at"]),
        ]

    @property
    def is_active(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    @classmethod
    def create_for_user(cls, *, user, token_hash: str, expires_at):
        now = timezone.now()
        cls.objects.filter(
            user=user,
            used_at__isnull=True,
            expires_at__gt=now,
        ).update(used_at=now)
        return cls.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    def mark_used(self):
        if self.used_at is None:
            self.used_at = timezone.now()
            self.save(update_fields=["used_at"])

    def __str__(self):
        return f"{self.user_id} {self.expires_at}"


class TenantInviteEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        RESENT = "RESENT", "Resent"
        REVOKED = "REVOKED", "Revoked"
        ACCEPTED = "ACCEPTED", "Accepted"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="invite_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_invite_events",
    )
    email = models.EmailField()
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "email"]),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tenant_id} {self.event_type} {self.email}"
