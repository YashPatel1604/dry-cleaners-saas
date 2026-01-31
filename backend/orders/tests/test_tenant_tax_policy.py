import itertools

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from orders.services import recalc_order_totals
from payments.models import Payment
from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety
_phone_seq = itertools.count(1)


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


def create_order_with_item(*, tenant, price_cents: int) -> Order:
    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone=f"7144000{next(_phone_seq):03d}",
    )
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


@pytest.mark.django_db
def test_tax_disabled_sets_tax_to_zero(django_user_model):
    tenant = Tenant.objects.create(
        slug="t-tax-off",
        name="T Tax Off",
        collects_tax=False,
        tax_rate_bps=725,
    )
    order = create_order_with_item(tenant=tenant, price_cents=1000)

    recalc_order_totals(order)
    order.refresh_from_db()

    assert order.tax_cents == 0
    assert order.total_cents == order.subtotal_cents


@pytest.mark.django_db
def test_tax_enabled_uses_custom_rate_with_correct_rounding(django_user_model):
    tenant = Tenant.objects.create(
        slug="t-tax-on",
        name="T Tax On",
        collects_tax=True,
        tax_rate_bps=725,
    )
    order = create_order_with_item(tenant=tenant, price_cents=1000)

    recalc_order_totals(order)
    order.refresh_from_db()

    expected_tax = int(round(1000 * 0.0725))
    assert order.tax_cents == expected_tax
    assert order.total_cents == order.subtotal_cents + expected_tax


@pytest.mark.django_db
def test_changing_rate_affects_unsettled_only(django_user_model):
    tenant = Tenant.objects.create(
        slug="t-tax-change",
        name="T Tax Change",
        collects_tax=True,
        tax_rate_bps=500,
    )
    order = create_order_with_item(tenant=tenant, price_cents=1000)

    recalc_order_totals(order)
    order.refresh_from_db()
    tax1 = order.tax_cents

    tenant.tax_rate_bps = 1000
    tenant.save(update_fields=["tax_rate_bps"])

    recalc_order_totals(order)
    order.refresh_from_db()
    tax2 = order.tax_cents

    assert tax2 != tax1
    assert tax2 == int(round(1000 * 0.10))


@pytest.mark.django_db
def test_settled_snapshot_immutable_after_policy_change(django_user_model):
    tenant = Tenant.objects.create(
        slug="t-tax-settle",
        name="T Tax Settle",
        collects_tax=True,
        tax_rate_bps=800,
    )
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = create_order_with_item(tenant=tenant, price_cents=1000)
    recalc_order_totals(order)
    order.refresh_from_db()

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=order.total_cents,
        reference="settle-pay",
    )
    recalc_order_totals(order)
    Order.objects.filter(id=order.id).update(status="COMPLETED")

    resp = client.post(f"/api/orders/{order.id}/settle/")
    assert resp.status_code == 200
    order.refresh_from_db()
    assert order.settled_at is not None

    settled_total = order.settled_total_cents
    settled_paid = order.settled_paid_cents

    tenant.collects_tax = False
    tenant.tax_rate_bps = 0
    tenant.save(update_fields=["collects_tax", "tax_rate_bps"])

    order.refresh_from_db()
    assert order.settled_total_cents == settled_total
    assert order.settled_paid_cents == settled_paid


@pytest.mark.django_db
def test_guardrails_validation(django_user_model):
    tenant = Tenant.objects.create(slug="t-tax-guard", name="T Tax Guard")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.patch(
        "/api/tenants/defaults/",
        data={"tax_rate_bps": 2500},
        format="json",
    )
    assert resp.status_code == 400

    resp = client.patch(
        "/api/tenants/defaults/",
        data={"tax_rate_bps": -1},
        format="json",
    )
    assert resp.status_code == 400

    invalid_tenant = Tenant(
        slug="t-tax-guard-model",
        name="T Tax Guard Model",
        tax_rate_bps=2500,
    )
    with pytest.raises(ValidationError):
        invalid_tenant.full_clean()
