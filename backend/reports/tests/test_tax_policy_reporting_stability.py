from datetime import date, datetime, time, timedelta
import itertools

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order
from orders.models import OrderItem
from orders.services import recalc_order_totals
from payments.models import Payment
from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety
_phone_seq = itertools.count(1)


def build_client(
    *,
    tenant,
    user,
    role=TenantMembership.Role.OWNER_ADMIN,
    is_active: bool = True,
) -> APIClient:
    membership, created = TenantMembership.objects.get_or_create(
        tenant=tenant,
        user=user,
        defaults={"role": role, "is_active": is_active},
    )
    if not created and (membership.role != role or membership.is_active != is_active):
        membership.role = role
        membership.is_active = is_active
        membership.save(update_fields=["role", "is_active"])
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


def create_order(*, tenant) -> Order:
    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone=f"7148000{next(_phone_seq):03d}",
    )
    return Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        due_at=timezone.now(),
    )


def create_inventory_item(*, tenant, name: str, price_cents: int) -> InventoryItem:
    item = InventoryItem(tenant=tenant, name=name)
    field_names = {f.name for f in InventoryItem._meta.get_fields() if hasattr(f, "attname")}
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
def test_tax_policy_reporting_stability(django_user_model):
    tenant_a = Tenant.objects.create(
        slug="t-tax-rep-a",
        name="T Tax Rep A",
        collects_tax=True,
        tax_rate_bps=800,
    )
    tenant_b = Tenant.objects.create(
        slug="t-tax-rep-b",
        name="T Tax Rep B",
        collects_tax=False,
        tax_rate_bps=800,
    )
    user = django_user_model.objects.create_user(username="u1", password="pw")

    order_a = create_order(tenant=tenant_a)
    order_b = create_order(tenant=tenant_b)

    item_a = create_inventory_item(tenant=tenant_a, name="Shirt", price_cents=1000)
    OrderItem.objects.create(
        tenant=tenant_a,
        order=order_a,
        item=item_a,
        quantity=1,
        unit_price_cents=1000,
        line_total_cents=1000,
    )

    item_b = create_inventory_item(tenant=tenant_b, name="Shirt", price_cents=1000)
    OrderItem.objects.create(
        tenant=tenant_b,
        order=order_b,
        item=item_b,
        quantity=1,
        unit_price_cents=1000,
        line_total_cents=1000,
    )

    recalc_order_totals(order_a)
    recalc_order_totals(order_b)
    order_a.refresh_from_db()
    order_b.refresh_from_db()

    Payment.objects.create(
        tenant=tenant_a,
        order=order_a,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=order_a.total_cents,
        reference="tax-rep-a",
    )
    Payment.objects.create(
        tenant=tenant_b,
        order=order_b,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=order_b.total_cents,
        reference="tax-rep-b",
    )

    Order.objects.filter(id=order_a.id).update(status="COMPLETED")
    Order.objects.filter(id=order_b.id).update(status="COMPLETED")

    client_a = build_client(tenant=tenant_a, user=user)
    client_b = build_client(tenant=tenant_b, user=user)

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    Order.objects.filter(id=order_a.id).update(settled_at=start + timedelta(hours=1))
    Order.objects.filter(id=order_b.id).update(settled_at=start + timedelta(hours=1))

    client_a.post(f"/api/orders/{order_a.id}/settle/")
    client_b.post(f"/api/orders/{order_b.id}/settle/")

    resp_a = client_a.get(
        "/api/reports/settlement-breakdown/?start=2026-01-15&end=2026-01-15"
    )
    resp_b = client_b.get(
        "/api/reports/settlement-breakdown/?start=2026-01-15&end=2026-01-15"
    )

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    data_a = resp_a.json()
    data_b = resp_b.json()

    assert data_a["tax_cents"] > 0
    assert data_b["tax_cents"] == 0
