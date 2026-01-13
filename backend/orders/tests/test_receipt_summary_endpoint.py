import pytest

pytestmark = pytest.mark.operator_safety
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant
from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from payments.models import Payment, Adjustment


def create_inventory_item(*, tenant, name: str, price_cents: int) -> InventoryItem:
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


@pytest.mark.django_db
def test_receipt_summary_matches_receipt_financials(django_user_model):
    tenant = Tenant.objects.create(slug="t-summary", name="T Summary")
    user = django_user_model.objects.create_user(username="u-summary", password="pw")

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000008",
    )

    inv = create_inventory_item(tenant=tenant, name="Shirt", price_cents=1000)

    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        due_at=timezone.now(),
    )
    OrderItem.objects.create(
        tenant=tenant,
        order=order,
        item=inv,
        quantity=1,
        unit_price_cents=1000,
        line_total_cents=1000,
    )

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=500,
        reference="p-summary-1",
    )
    Adjustment.objects.create(
        tenant=tenant,
        order=order,
        kind=Adjustment.Kind.OTHER,
        status=Adjustment.Status.APPLIED,
        direction=Adjustment.Direction.IN,
        amount_cents=200,
        reference="a-summary-1",
        note="credit",
    )

    api = APIClient()
    api.force_authenticate(user=user)
    api.credentials(HTTP_X_TENANT=tenant.slug)

    receipt = api.get(f"/api/orders/{order.id}/receipt/")
    assert receipt.status_code == 200
    receipt_data = receipt.json()

    summary = api.get(f"/api/orders/{order.id}/receipt/summary/")
    assert summary.status_code == 200
    summary_data = summary.json()

    expected_fields = {
        "id",
        "status",
        "due_at",
        "notes",
        "created_at",
        "settled_at",
        "customer",
        "subtotal_cents",
        "tax_cents",
        "total_cents",
        "paid_cents",
        "adjustments_net_cents",
        "net_paid_cents",
        "balance_due_cents",
        "change_due_cents",
    }

    assert set(summary_data.keys()) == expected_fields
    for field in expected_fields:
        assert summary_data[field] == receipt_data[field]

    assert "items" not in summary_data
    assert "payments" not in summary_data
    assert "adjustments" not in summary_data
