# orders/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

from tenants.models import Tenant
from customers.models import Customer
from inventory.models import InventoryItem


class Order(models.Model):
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="orders"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders"
    )

    status = models.CharField(max_length=20, default="RECEIVED")
    due_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    # ✅ lifecycle timestamps (v0.3.1)
    received_at = models.DateTimeField(null=True, blank=True)
    in_progress_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)

    # accounting fields
    subtotal_cents = models.PositiveIntegerField(default=0)
    tax_cents = models.PositiveIntegerField(default=0)
    total_cents = models.PositiveIntegerField(default=0)
    paid_cents = models.IntegerField(default=0)
    settled_at = models.DateTimeField(null=True, blank=True)

    settled_total_cents = models.IntegerField(null=True, blank=True)
    settled_paid_cents = models.IntegerField(null=True, blank=True)
    settled_change_cents = models.IntegerField(null=True, blank=True)
    settled_balance_due_cents = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "status", "created_at"]),
            models.Index(fields=["tenant", "customer", "created_at"]),
        ]


class OrderStatusEvent(models.Model):
    """
    Immutable audit log of order status transitions.
    """
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="order_status_events"
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_events"
    )

    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_status_events",
    )

    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["tenant", "order", "created_at"]),
            models.Index(fields=["tenant", "created_at"]),
        ]

    def __str__(self):
        return f"{self.order_id}: {self.from_status} -> {self.to_status}"


class OrderItem(models.Model):
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="order_items"
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )

    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=1)

    unit_price_cents = models.PositiveIntegerField()
    line_total_cents = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "order"]),
            models.Index(fields=["tenant", "item"]),
        ]

    def save(self, *args, **kwargs):
        self.line_total_cents = self.quantity * self.unit_price_cents
        super().save(*args, **kwargs)
