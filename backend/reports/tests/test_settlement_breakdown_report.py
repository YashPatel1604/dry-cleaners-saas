from datetime import date, datetime, time, timedelta
import itertools

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
from payments.models import Adjustment
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


def create_order(*, tenant, status: str) -> Order:
    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone=f"7143000{next(_phone_seq):03d}",
    )
    return Order.objects.create(
        tenant=tenant,
        customer=customer,
        status=status,
        due_at=timezone.now(),
    )


@pytest.mark.django_db
def test_settlement_breakdown_report_range(django_user_model):
    tenant = Tenant.objects.create(slug="t-settle", name="T Settle")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    day1 = date(2026, 1, 15)
    day2 = date(2026, 1, 16)
    tz = timezone.get_current_timezone()
    start1 = timezone.make_aware(datetime.combine(day1, time.min), tz)
    start2 = timezone.make_aware(datetime.combine(day2, time.min), tz)

    order1 = create_order(tenant=tenant, status="COMPLETED")
    order2 = create_order(tenant=tenant, status="COMPLETED")

    Order.objects.filter(id=order1.id).update(
        settled_at=start1 + timedelta(hours=1),
        settled_total_cents=2000,
        settled_paid_cents=2500,
        settled_change_cents=500,
        settled_balance_due_cents=0,
        subtotal_cents=1800,
        tax_cents=200,
    )
    Order.objects.filter(id=order2.id).update(
        settled_at=start2 + timedelta(hours=2),
        settled_total_cents=1500,
        settled_paid_cents=1500,
        settled_change_cents=0,
        settled_balance_due_cents=0,
        subtotal_cents=1400,
        tax_cents=100,
    )

    adj_in = Adjustment.objects.create(
        tenant=tenant,
        order=order1,
        status=Adjustment.Status.APPLIED,
        direction=Adjustment.Direction.IN,
        amount_cents=100,
        reference="adj-in",
    )
    adj_out = Adjustment.objects.create(
        tenant=tenant,
        order=order2,
        status=Adjustment.Status.APPLIED,
        direction=Adjustment.Direction.OUT,
        amount_cents=50,
        reference="adj-out",
    )

    Adjustment.objects.filter(id=adj_in.id).update(created_at=start1 + timedelta(hours=3))
    Adjustment.objects.filter(id=adj_out.id).update(created_at=start2 + timedelta(hours=4))

    resp = client.get(
        "/api/reports/settlement-breakdown/?start=2026-01-15&end=2026-01-16"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["subtotal_cents"] == 3200
    assert data["tax_cents"] == 300
    assert data["total_cents"] == 3500
    assert data["adjustments_in_cents"] == 100
    assert data["adjustments_out_cents"] == 50
    assert data["adjustments_net_cents"] == 50
    assert data["paid_cents"] == 4000
    assert data["change_cents"] == 500
    assert data["balance_due_cents"] == 0


@pytest.mark.django_db
def test_settlement_breakdown_report_tenant_isolated(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-settle-a", name="T Settle A")
    tenant_b = Tenant.objects.create(slug="t-settle-b", name="T Settle B")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant_a, user=user)

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)

    order_b = create_order(tenant=tenant_b, status="COMPLETED")
    Order.objects.filter(id=order_b.id).update(
        settled_at=start + timedelta(hours=1),
        settled_total_cents=1000,
        settled_paid_cents=1000,
        settled_change_cents=0,
        settled_balance_due_cents=0,
        subtotal_cents=900,
        tax_cents=100,
    )

    resp = client.get(
        "/api/reports/settlement-breakdown/?start=2026-01-15&end=2026-01-15"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["subtotal_cents"] == 0
    assert data["tax_cents"] == 0
    assert data["total_cents"] == 0
    assert data["adjustments_in_cents"] == 0
    assert data["adjustments_out_cents"] == 0
    assert data["adjustments_net_cents"] == 0
    assert data["paid_cents"] == 0
    assert data["change_cents"] == 0
    assert data["balance_due_cents"] == 0


@pytest.mark.django_db
def test_settlement_breakdown_report_validation(django_user_model):
    tenant = Tenant.objects.create(slug="t-settle-val", name="T Settle Val")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get("/api/reports/settlement-breakdown/?start=2026-01-16")
    assert resp.status_code == 400

    resp = client.get(
        "/api/reports/settlement-breakdown/?start=2026-01-16&end=2026-01-15"
    )
    assert resp.status_code == 400
