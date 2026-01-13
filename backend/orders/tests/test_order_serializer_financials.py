import pytest

pytestmark = pytest.mark.operator_safety
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant
from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from payments.models import Payment, Adjustment
from orders.services import recalc_order_totals


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


def build_client(*, tenant, user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


def create_order_with_item(*, tenant, customer, price_cents: int) -> Order:
    inv = create_inventory_item(tenant=tenant, name="Shirt", price_cents=price_cents)
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
        unit_price_cents=price_cents,
        line_total_cents=price_cents,
    )
    return order


@pytest.mark.django_db
def test_order_serializer_financials_payments_only(django_user_model):
    tenant = Tenant.objects.create(slug="t1", name="T1")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000000",
    )

    order = create_order_with_item(tenant=tenant, customer=customer, price_cents=1000)

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1000,
        reference="p-1",
    )

    recalc_order_totals(order)

    resp = client.get(f"/api/orders/{order.id}/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["net_paid_cents"] == 1000
    assert data["balance_due_cents"] == 80
    assert data["change_due_cents"] == 0


@pytest.mark.django_db
def test_order_serializer_financials_adjustments_affect_net_paid(django_user_model):
    tenant = Tenant.objects.create(slug="t2", name="T2")
    user = django_user_model.objects.create_user(username="u2", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000001",
    )

    order = create_order_with_item(tenant=tenant, customer=customer, price_cents=1000)

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=500,
        reference="p-2",
    )

    Adjustment.objects.create(
        tenant=tenant,
        order=order,
        kind=Adjustment.Kind.OTHER,
        status=Adjustment.Status.APPLIED,
        direction=Adjustment.Direction.IN,
        amount_cents=200,
        reference="a-1",
        note="credit",
    )

    recalc_order_totals(order)

    resp = client.get(f"/api/orders/{order.id}/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["net_paid_cents"] == 700
    assert data["balance_due_cents"] == 380
    assert data["change_due_cents"] == 0


@pytest.mark.django_db
def test_order_serializer_financials_overpay_without_out_payment(django_user_model):
    tenant = Tenant.objects.create(slug="t3", name="T3")
    user = django_user_model.objects.create_user(username="u3", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000002",
    )

    order = create_order_with_item(tenant=tenant, customer=customer, price_cents=1000)

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1500,
        reference="p-3",
    )

    recalc_order_totals(order)

    resp = client.get(f"/api/orders/{order.id}/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["net_paid_cents"] == 1500
    assert data["balance_due_cents"] == 0
    assert data["change_due_cents"] == 420


@pytest.mark.django_db
def test_order_serializer_financials_out_payment_zeroes_change_due(django_user_model):
    tenant = Tenant.objects.create(slug="t4", name="T4")
    user = django_user_model.objects.create_user(username="u4", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000003",
    )

    order = create_order_with_item(tenant=tenant, customer=customer, price_cents=1000)

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1500,
        reference="p-4-in",
    )
    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=200,
        reference="p-4-out",
        note="change",
    )

    recalc_order_totals(order)

    resp = client.get(f"/api/orders/{order.id}/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["net_paid_cents"] == 1300
    assert data["balance_due_cents"] == 0
    assert data["change_due_cents"] == 0


@pytest.mark.django_db
def test_order_serializer_financials_present_on_list(django_user_model):
    tenant = Tenant.objects.create(slug="t5", name="T5")
    user = django_user_model.objects.create_user(username="u5", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000004",
    )

    order = create_order_with_item(tenant=tenant, customer=customer, price_cents=1000)

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1000,
        reference="p-5",
    )

    recalc_order_totals(order)

    resp = client.get("/api/orders/")
    assert resp.status_code == 200
    data = resp.json()

    results = data if isinstance(data, list) else data.get("results", [])
    assert isinstance(results, list)
    assert len(results) == 1

    row = results[0]
    assert row["net_paid_cents"] == 1000
    assert row["balance_due_cents"] == 80
    assert row["change_due_cents"] == 0
