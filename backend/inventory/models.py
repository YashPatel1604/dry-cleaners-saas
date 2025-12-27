from django.db import models
from tenants.models import Tenant


class InventoryItem(models.Model):
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="inventory_items")

    name = models.CharField(max_length=120)          # e.g. "Shirt"
    sku = models.CharField(max_length=40, blank=True)
    unit_price_cents = models.PositiveIntegerField()  # e.g. 399
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("tenant", "name")]
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "name"]),
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.tenant.slug})"
