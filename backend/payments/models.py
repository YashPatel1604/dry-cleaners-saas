# payments/models.py
from django.db import models
from django.db.models import Q

from tenants.models import Tenant
from orders.models import Order


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        ONLINE = "ONLINE", "Online"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        CAPTURED = "CAPTURED", "Captured"  # counts in totals
        VOIDED = "VOIDED", "Voided"        # ignored

    class Direction(models.TextChoices):
        IN = "IN", "In"     # customer pays you
        OUT = "OUT", "Out"  # you refund customer

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="order_payments",
        related_query_name="order_payment",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.CAPTURED
    )
    direction = models.CharField(
        max_length=3, choices=Direction.choices, default=Direction.IN
    )

    amount_cents = models.PositiveIntegerField()

    # ✅ Keep reference as "" when not provided (no nulls)
    reference = models.CharField(max_length=120, blank=True, default="")

    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # ✅ Unique per tenant only when reference != ""
            models.UniqueConstraint(
                fields=["tenant", "reference"],
                condition=~Q(reference=""),
                name="uniq_payment_reference_per_tenant_nonempty",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "order"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "reference"]),
        ]

    def __str__(self):
        return f"{self.tenant_id} {self.order_id} {self.direction} {self.amount_cents} {self.status}"


class Adjustment(models.Model):
    """
    Post-settlement accounting adjustments.
    Does NOT change Payment rows.
    Affects receipt and summaries.
    """

    class Kind(models.TextChoices):
        REFUND = "REFUND", "Refund"
        CHARGEBACK = "CHARGEBACK", "Chargeback"
        WRITE_OFF = "WRITE_OFF", "Write-off"
        CREDIT_APPLIED = "CREDIT_APPLIED", "Credit applied"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Applied"
        VOIDED = "VOIDED", "Voided"

    class Direction(models.TextChoices):
        IN = "IN", "In"     # money/value came in (rare post-settle)
        OUT = "OUT", "Out"  # money/value went out (refund/write-off/etc.)

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="order_adjustments",
        related_query_name="order_adjustment",
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="adjustments")

    kind = models.CharField(
        max_length=30, choices=Kind.choices, default=Kind.OTHER)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.APPLIED)
    direction = models.CharField(
        max_length=3, choices=Direction.choices, default=Direction.OUT)

    amount_cents = models.PositiveIntegerField()
    reference = models.CharField(max_length=120, blank=True, null=True)
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "reference"],
                condition=(~Q(reference="") & ~Q(reference__isnull=True)),
                name="uniq_adjustment_reference_per_tenant_nonempty",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "order"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "reference"]),
        ]

    def __str__(self):
        return f"{self.tenant_id} {self.order_id} {self.kind} {self.direction} {self.amount_cents} {self.status}"
