# orders/models.py
from django.db import models
from tenants.models import Tenant
from customers.models import Customer
from inventory.models import InventoryItem


class Order(models.Model):
    # your existing fields...
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="orders")
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, default="RECEIVED")
    due_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    # keep these for now, but we'll start auto-filling them
    subtotal_cents = models.PositiveIntegerField(default=0)
    tax_cents = models.PositiveIntegerField(default=0)
    total_cents = models.PositiveIntegerField(default=0)
    paid_cents = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="order_items")
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items")

    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)

    unit_price_cents = models.PositiveIntegerField()  # snapshot at time of order
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
