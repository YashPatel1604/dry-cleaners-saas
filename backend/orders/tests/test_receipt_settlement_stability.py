from django.test import TestCase
import pytest

pytestmark = pytest.mark.operator_safety
from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework.test import APIClient

from tenants.models import Tenant
from customers.models import Customer
from orders.models import Order, OrderItem
from inventory.models import InventoryItem
from payments.models import Payment

User = get_user_model()


def create_inventory_item(*, tenant, name: str, price_cents: int) -> InventoryItem:
    """
    InventoryItem fields may vary. This helper sets an existing price field dynamically.
    """
    item = InventoryItem(tenant=tenant, name=name)

    field_names = {f.name for f in InventoryItem._meta.get_fields()
                   if hasattr(f, "attname")}
    candidates = [
        "price_cents",
        "unit_price_cents",
        "default_price_cents",
        "base_price_cents",
        "price",
        "base_price",
    ]

    for fname in candidates:
        if fname in field_names:
            setattr(item, fname, price_cents)
            item.save()
            return item

    raise AssertionError(
        f"Could not find a price field on InventoryItem. Fields: {sorted(field_names)}")


class TestReceiptSettlementStability(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(name="T1", slug="t1")
        self.user = User.objects.create_user(username="admin", password="pass")

        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT=self.tenant.slug)

        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="Patel",
            phone="7140000000",
        )

        self.inv = create_inventory_item(
            tenant=self.tenant, name="Shirt", price_cents=1000)

        # Create a COMPLETED order with a $10.00 item and a $10.00 payment
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            status="COMPLETED",
            due_at=timezone.now(),
        )

        OrderItem.objects.create(
            tenant=self.tenant,
            order=self.order,
            item=self.inv,
            quantity=1,
            unit_price_cents=1000,
        )

        Payment.objects.create(
            tenant=self.tenant,
            order=self.order,
            method=Payment.Method.CASH,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.IN,
            amount_cents=5000,
            reference="p-1",
        )

    def test_receipt_totals_do_not_change_after_settlement(self):
        # 1) Settle the order (this creates settled_* snapshot fields)
        # Ensure totals are computed before settlement (paid_cents/total_cents populated)
        _ = self.client.get(f"/api/orders/{self.order.id}/receipt/")
        r_settle = self.client.post(
            f"/api/orders/{self.order.id}/settle/", data={}, format="json")
        self.assertEqual(r_settle.status_code, 200)

        # Pull the persisted settlement snapshot from the DB
        self.order.refresh_from_db()
        settled_total = self.order.settled_total_cents
        settled_paid = self.order.settled_paid_cents
        settled_change = self.order.settled_change_cents
        settled_balance = self.order.settled_balance_due_cents

        self.assertIsNotNone(self.order.settled_at)
        self.assertIsNotNone(settled_total)
        self.assertIsNotNone(settled_paid)
        self.assertIsNotNone(settled_change)
        self.assertIsNotNone(settled_balance)

        # 2) Simulate a "rogue" payment inserted after settlement (should NOT affect reprint receipt)
        Payment.objects.create(
            tenant=self.tenant,
            order=self.order,
            method=Payment.Method.CASH,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.IN,
            amount_cents=500,
            reference="p-rogue",
        )

        # 3) Reprint receipt
        r_receipt = self.client.get(f"/api/orders/{self.order.id}/receipt/")
        self.assertEqual(r_receipt.status_code, 200)
        data = r_receipt.json()

        # The displayed totals should stick to settlement snapshot
        self.assertEqual(data["total_cents"], settled_total)
        self.assertEqual(data["paid_cents"], settled_paid)
        self.assertEqual(data["change_due_cents"], settled_change)
        self.assertEqual(data["balance_due_cents"], settled_balance)
