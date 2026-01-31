from datetime import date, datetime, time, timedelta
import itertools

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
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
        phone=f"7141000{next(_phone_seq):03d}",
    )
    return Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        due_at=timezone.now(),
    )


@pytest.mark.django_db
def test_cash_drawer_sums(django_user_model):
    tenant = Tenant.objects.create(slug="t-cash", name="T Cash")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = create_order(tenant=tenant)
    cash_in = Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1200,
        reference="cash-in",
    )
    cash_out = Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=300,
        reference="cash-out",
        note="Cash out",
    )

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    Payment.objects.filter(id__in=[cash_in.id, cash_out.id]).update(
        created_at=start + timedelta(hours=2)
    )

    resp = client.get(f"/api/reports/cash-drawer/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["cash"] == {"in_cents": 1200, "out_cents": 300, "net_cents": 900}
    assert data["breakdown"] == {
        "change_paid_out_cents": 0,
        "refunds_cash_out_cents": 0,
        "other_cash_out_cents": 300,
    }
    assert data["notes"] == [
        "Breakdown unavailable without semantic payment fields; all cash-out recorded as other."
    ]


@pytest.mark.django_db
def test_cash_drawer_breakdown_classification(django_user_model):
    tenant = Tenant.objects.create(slug="t-cash-breakdown", name="T Cash Breakdown")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = create_order(tenant=tenant)
    change_out = Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=200,
        reference="ref-1-change",
        note="Auto change-out",
    )
    refund_out = Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=150,
        reference="ref-2",
        note="Refund payout",
    )
    other_out = Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=50,
        reference="ref-3",
        note="Cash out",
    )

    day = date(2026, 1, 16)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    Payment.objects.filter(id__in=[change_out.id, refund_out.id, other_out.id]).update(
        created_at=start + timedelta(hours=1)
    )

    resp = client.get(f"/api/reports/cash-drawer/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["breakdown"] == {
        "change_paid_out_cents": 200,
        "refunds_cash_out_cents": 150,
        "other_cash_out_cents": 50,
    }
    assert data["notes"] == []


@pytest.mark.django_db
def test_cash_drawer_tenant_isolated(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-cash-a", name="T Cash A")
    tenant_b = Tenant.objects.create(slug="t-cash-b", name="T Cash B")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant_a, user=user)

    order_b = create_order(tenant=tenant_b)
    payment_b = Payment.objects.create(
        tenant=tenant_b,
        order=order_b,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=999,
        reference="cash-b",
    )

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    Payment.objects.filter(id=payment_b.id).update(created_at=start + timedelta(hours=1))

    resp = client.get(f"/api/reports/cash-drawer/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["cash"] == {"in_cents": 0, "out_cents": 0, "net_cents": 0}
    assert data["breakdown"] == {
        "change_paid_out_cents": 0,
        "refunds_cash_out_cents": 0,
        "other_cash_out_cents": 0,
    }
    assert data["notes"] == []
