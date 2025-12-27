from django.db import models
from tenants.scoping import TenantScopedModel


# -------------------------
# Billing (Invoices/Payments)
# -------------------------

class Invoice(TenantScopedModel):
    """
    Billing document for a single Order.
    Editable later via notes + adjustments.
    """
    order = models.OneToOneField(
        "orders.Order", on_delete=models.PROTECT, related_name="invoice")

    invoice_number = models.PositiveIntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)

    # Snapshot values (generated)
    generated_amount_cents = models.PositiveIntegerField(default=0)

    # Manual overrides/adjustments
    manual_adjustment_cents = models.IntegerField(
        default=0)  # can be negative or positive
    notes = models.TextField(blank=True)

    is_locked = models.BooleanField(default=False)  # lock after finalization
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "invoice_number"], name="uniq_invoice_number_per_tenant"),
        ]
        indexes = [
            models.Index(fields=["tenant", "issued_at"]),
        ]

    @property
    def total_amount_cents(self) -> int:
        return int(self.generated_amount_cents) + int(self.manual_adjustment_cents)

    def __str__(self):
        return f"{self.tenant.slug} INV-{self.invoice_number}"


class Payment(TenantScopedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        OTHER = "OTHER", "Other"

    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="payments")

    method = models.CharField(
        max_length=10, choices=Method.choices, default=Method.CARD)
    amount_cents = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
        ]


# -------------------------
# Editable Reports (Summaries)
# -------------------------

class Report(TenantScopedModel):
    """
    Editable summary document (daily/weekly/monthly).
    Stores generated snapshot + allows manual edits via ReportLine and manual_total override.
    """
    class Kind(models.TextChoices):
        DAILY_SUMMARY = "DAILY_SUMMARY", "Daily Summary"
        WEEKLY_SUMMARY = "WEEKLY_SUMMARY", "Weekly Summary"
        MONTHLY_SUMMARY = "MONTHLY_SUMMARY", "Monthly Summary"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=140)

    start_date = models.DateField()
    end_date = models.DateField()

    # Snapshot total (generated)
    generated_total_cents = models.PositiveIntegerField(default=0)

    # Optional manual override total
    manual_total_cents = models.IntegerField(null=True, blank=True)

    notes = models.TextField(blank=True)
    is_locked = models.BooleanField(default=False)

    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "kind", "start_date", "end_date"]),
            models.Index(fields=["tenant", "generated_at"]),
        ]

    @property
    def effective_total_cents(self) -> int:
        return int(self.manual_total_cents) if self.manual_total_cents is not None else int(self.generated_total_cents)

    def __str__(self):
        return f"{self.tenant.slug} {self.kind} {self.start_date}–{self.end_date}"


class ReportLine(TenantScopedModel):
    """
    Editable breakdown lines in a report.
    """
    report = models.ForeignKey(
        Report, on_delete=models.CASCADE, related_name="lines")

    label = models.CharField(max_length=200)  # e.g. "Dry Cleaning Revenue"
    amount_cents = models.IntegerField(default=0)  # allow negative adjustments
    sort_order = models.PositiveIntegerField(default=0)

    # If you generate lines from system, set False. Manual edits are True.
    is_manual = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["tenant", "report"]),
        ]

    def __str__(self):
        return self.label


class ReportRevision(TenantScopedModel):
    """
    Optional: version history for auditability.
    We store a JSON snapshot of Report + lines before changes.
    """
    report = models.ForeignKey(
        Report, on_delete=models.CASCADE, related_name="revisions")
    edited_by_user_id = models.IntegerField()
    snapshot_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "report"]),
        ]
