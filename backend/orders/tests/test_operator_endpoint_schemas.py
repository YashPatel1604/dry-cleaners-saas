import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from payments.models import Payment
from tenants.models import Tenant

pytestmark = pytest.mark.operator_safety


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


def build_order_with_item(*, tenant, customer, status: str) -> Order:
    inv = create_inventory_item(tenant=tenant, name="Shirt", price_cents=1000)
    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status=status,
        due_at=timezone.now(),
        received_at=timezone.now(),
    )
    OrderItem.objects.create(
        tenant=tenant,
        order=order,
        item=inv,
        quantity=1,
        unit_price_cents=1000,
        line_total_cents=1000,
    )
    return order


def build_client(*, tenant, user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


@pytest.mark.django_db
def test_receipt_endpoint_schema(django_user_model):
    tenant = Tenant.objects.create(slug="t-receipt", name="T Receipt")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000010",
    )

    order = build_order_with_item(tenant=tenant, customer=customer, status="RECEIVED")

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=500,
        reference="p-receipt",
    )

    resp = client.get(f"/api/orders/{order.id}/receipt/")
    assert resp.status_code == 200
    data = resp.json()

    expected_fields = {
        "id",
        "status",
        "due_at",
        "notes",
        "created_at",
        "settled_at",
        "customer",
        "items",
        "subtotal_cents",
        "tax_cents",
        "total_cents",
        "paid_cents",
        "adjustments_net_cents",
        "net_paid_cents",
        "balance_due_cents",
        "change_due_cents",
        "payments",
        "adjustments",
    }
    assert set(data.keys()) == expected_fields
    assert isinstance(data["items"], list)
    assert isinstance(data["payments"], list)
    assert isinstance(data["adjustments"], list)

    if data["items"]:
        item_keys = {
            "id",
            "item",
            "item_name",
            "sku",
            "quantity",
            "unit_price_cents",
            "line_total_cents",
        }
        assert set(data["items"][0].keys()) == item_keys

    if data["payments"]:
        payment_keys = {
            "id",
            "method",
            "status",
            "direction",
            "amount_cents",
            "reference",
            "note",
            "created_at",
        }
        assert set(data["payments"][0].keys()) == payment_keys


@pytest.mark.django_db
def test_receipt_summary_endpoint_schema(django_user_model):
    tenant = Tenant.objects.create(slug="t-summary", name="T Summary")
    user = django_user_model.objects.create_user(username="u2", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000011",
    )

    order = build_order_with_item(tenant=tenant, customer=customer, status="RECEIVED")

    resp = client.get(f"/api/orders/{order.id}/receipt/summary/")
    assert resp.status_code == 200
    data = resp.json()

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
    assert set(data.keys()) == expected_fields


@pytest.mark.django_db
def test_pickup_payment_endpoint_schema(django_user_model):
    tenant = Tenant.objects.create(slug="t-pickup-pay", name="T Pickup Pay")
    user = django_user_model.objects.create_user(username="u3", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000012",
    )

    order = build_order_with_item(tenant=tenant, customer=customer, status="READY")

    resp = client.post(
        f"/api/orders/{order.id}/pickup-payment/",
        data={
            "amount_cents": 1500,
            "method": "CASH",
            "reference": "pickup-pay-1",
            "note": "overpay",
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert set(data.keys()) == {"payment", "change_payment", "order"}

    payment_keys = {
        "id",
        "order",
        "method",
        "status",
        "direction",
        "amount_cents",
        "reference",
        "note",
        "created_at",
    }
    assert set(data["payment"].keys()) == payment_keys
    assert set(data["change_payment"].keys()) == payment_keys

    order_keys = {
        "id",
        "customer",
        "status",
        "due_at",
        "notes",
        "subtotal_cents",
        "tax_cents",
        "total_cents",
        "paid_cents",
        "net_paid_cents",
        "balance_due_cents",
        "change_due_cents",
        "settled_at",
        "created_at",
        "received_at",
        "in_progress_at",
        "ready_at",
        "completed_at",
        "cancelled_at",
        "picked_up_at",
    }
    assert set(data["order"].keys()) == order_keys


@pytest.mark.django_db
def test_pickup_endpoint_schema(django_user_model):
    tenant = Tenant.objects.create(slug="t-pickup", name="T Pickup")
    user = django_user_model.objects.create_user(username="u4", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000013",
    )

    order = build_order_with_item(tenant=tenant, customer=customer, status="READY")

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1080,
        reference="pickup-1",
    )

    resp = client.post(f"/api/orders/{order.id}/pickup/", data={}, format="json")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "PICKED_UP"
    assert "net_paid_cents" in data
    assert "balance_due_cents" in data
    assert "change_due_cents" in data


@pytest.mark.django_db
def test_settle_endpoint_schema(django_user_model):
    tenant = Tenant.objects.create(slug="t-settle", name="T Settle")
    user = django_user_model.objects.create_user(username="u5", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000014",
    )

    order = build_order_with_item(tenant=tenant, customer=customer, status="COMPLETED")

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1080,
        reference="settle-1",
    )

    resp = client.post(f"/api/orders/{order.id}/settle/", data={}, format="json")
    assert resp.status_code == 200
    data = resp.json()

    expected_fields = {
        "id",
        "status",
        "due_at",
        "notes",
        "created_at",
        "settled_at",
        "customer",
        "items",
        "subtotal_cents",
        "tax_cents",
        "total_cents",
        "paid_cents",
        "adjustments_net_cents",
        "net_paid_cents",
        "balance_due_cents",
        "change_due_cents",
        "payments",
        "adjustments",
    }
    assert set(data.keys()) == expected_fields
