# audit/models.py
import uuid
from django.db import models
from tenants.models import Tenant


class AuditEvent(models.Model):
    class ActorType(models.TextChoices):
        USER = "USER", "User"
        SYSTEM = "SYSTEM", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # Correlation
    request_id = models.CharField(max_length=64, blank=True, default="")

    # Actor (keep flexible; actor_id as string supports different auth/user pk types)
    actor_type = models.CharField(
        max_length=20, choices=ActorType.choices, default=ActorType.SYSTEM
    )
    actor_id = models.CharField(max_length=64, blank=True, default="")
    actor_label = models.CharField(max_length=255, blank=True, default="")

    # What happened
    action = models.CharField(max_length=80)        # e.g. "payment.created"
    entity_type = models.CharField(max_length=40)   # e.g. "payment", "order"
    # store as string for flexibility
    entity_id = models.CharField(max_length=64)

    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "request_id"]),
            models.Index(fields=["tenant", "entity_type",
                         "entity_id", "created_at"]),
            models.Index(fields=["tenant", "action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.tenant_id} {self.action} {self.entity_type}:{self.entity_id}"
