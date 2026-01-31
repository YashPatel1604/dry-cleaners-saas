from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
from customers.models import Customer
from orders.models import Order, OrderItem
from inventory.models import InventoryItem

User = get_user_model()


def create_inventory_item(*, tenant, name: str, price_cents: int) -> InventoryItem:
    """
    InventoryItem model fields may differ over time.
    This helper sets the correct required price field dynamically.
    """
    item = InventoryItem(tenant=tenant, name=name)

    field_names = {f.name for f in InventoryItem._meta.get_fields()
                   if hasattr(f, "attname")}

    # Common possibilities (try in order)
    candidates = [
        "price_cents",
        "unit_price_cents",
        "default_price_cents",
        "base_price_cents",
        "price",          # sometimes IntegerField
        "base_price",     # sometimes IntegerField
    ]

    set_ok = False
    for fname in candidates:
        if fname in field_names:
            setattr(item, fname, price_cents)
            set_ok = True
            break

    if not set_ok:
        raise AssertionError(
            f"Could not find a price field on InventoryItem. Fields: {sorted(field_names)}"
        )

    item.save()
    return item


class TestOrderLabels(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(name="T1", slug="t1")
        self.other_tenant = Tenant.objects.create(name="T2", slug="t2")

        self.user = User.objects.create_user(username="admin", password="pass")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantMembership.Role.OWNER_ADMIN,
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT=self.tenant.slug)

        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="Patel",
            phone="7140000000",
        )
        self.customer2 = Customer.objects.create(
            tenant=self.other_tenant,
            name="Other",
            phone="9490000000",
        )

        self.inv_shirt = create_inventory_item(
            tenant=self.tenant, name="Shirt", price_cents=500
        )
        self.inv_pants = create_inventory_item(
            tenant=self.tenant, name="Pants", price_cents=800
        )

        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            status="RECEIVED",
            due_at=timezone.now(),
        )

        # 2 shirts + 1 pants = 3 labels
        OrderItem.objects.create(
            tenant=self.tenant,
            order=self.order,
            item=self.inv_shirt,
            quantity=2,
            unit_price_cents=500,
        )
        OrderItem.objects.create(
            tenant=self.tenant,
            order=self.order,
            item=self.inv_pants,
            quantity=1,
            unit_price_cents=800,
        )

        self.other_order = Order.objects.create(
            tenant=self.other_tenant,
            customer=self.customer2,
            status="RECEIVED",
        )

    def test_labels_tenant_scoped(self):
        r = self.client.get(f"/api/orders/{self.other_order.id}/labels/")
        self.assertIn(r.status_code, (404, 403))

    def test_labels_expands_quantity(self):
        r = self.client.get(f"/api/orders/{self.order.id}/labels/")
        self.assertEqual(r.status_code, 200)

        data = r.json()
        self.assertEqual(data["order_id"], self.order.id)
        self.assertEqual(data["count"], 3)

        labels = data["labels"]
        self.assertEqual(len(labels), 3)

        # label_code format + sequential
        self.assertEqual(labels[0]["label_code"], f"ORD-{self.order.id}-001")
        self.assertEqual(labels[1]["label_code"], f"ORD-{self.order.id}-002")
        self.assertEqual(labels[2]["label_code"], f"ORD-{self.order.id}-003")

        # expected fields
        for i, lab in enumerate(labels, start=1):
            self.assertEqual(lab["sequence"], i)
            self.assertEqual(lab["order_id"], self.order.id)
            self.assertEqual(lab["customer_name"], "Patel")
            self.assertIn(lab["item_name"], ("Shirt", "Pants"))
            self.assertIsNotNone(lab["order_item_id"])
