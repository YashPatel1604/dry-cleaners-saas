import pytest

pytestmark = pytest.mark.operator_safety
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from payments.models import Payment


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


def build_order_with_item(*, tenant, customer, price_cents: int) -> Order:
    inv = create_inventory_item(tenant=tenant, name="Shirt", price_cents=price_cents)
    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        received_at=timezone.now(),
    )
    OrderItem.objects.create(
        tenant=tenant,
        order=order,
        item=inv,
        quantity=1,
        unit_price_cents=price_cents,
        line_total_cents=price_cents,
    )
    return order


@pytest.mark.django_db
def test_receipt_change_due_when_overpaid_without_out(django_user_model):
    tenant = Tenant.objects.create(slug="t-change-1", name="T Change 1")
    user = django_user_model.objects.create_user(username="u-change-1", password="pw")
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    )

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000006",
    )

    order = build_order_with_item(tenant=tenant, customer=customer, price_cents=1000)

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1500,
        reference="p-change-1",
    )

    api = APIClient()
    api.force_authenticate(user=user)
    api.credentials(HTTP_X_TENANT=tenant.slug)

    resp = api.get(f"/api/orders/{order.id}/receipt/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_cents"] == 1080
    assert data["net_paid_cents"] == 1500
    assert data["balance_due_cents"] == 0
    assert data["change_due_cents"] == 420


@pytest.mark.django_db
def test_receipt_change_due_zero_when_out_payment_exists(django_user_model):
    tenant = Tenant.objects.create(slug="t-change-2", name="T Change 2")
    user = django_user_model.objects.create_user(username="u-change-2", password="pw")
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    )

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000007",
    )

    order = build_order_with_item(tenant=tenant, customer=customer, price_cents=1000)

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1500,
        reference="p-change-2-in",
    )
    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=200,
        reference="p-change-2-out",
        note="change",
    )

    api = APIClient()
    api.force_authenticate(user=user)
    api.credentials(HTTP_X_TENANT=tenant.slug)

    resp = api.get(f"/api/orders/{order.id}/receipt/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_cents"] == 1080
    assert data["net_paid_cents"] == 1300
    assert data["balance_due_cents"] == 0
    assert data["change_due_cents"] == 0
