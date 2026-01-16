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


def create_order(*, tenant, status: str, due_at=None) -> Order:
    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone=f"7142000{next(_phone_seq):03d}",
    )
    return Order.objects.create(
        tenant=tenant,
        customer=customer,
        status=status,
        due_at=due_at,
    )


@pytest.mark.django_db
def test_revenue_report_range(django_user_model):
    tenant = Tenant.objects.create(slug="t-rev", name="T Rev")
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
        settled_at=start1 + timedelta(hours=2),
        settled_total_cents=3000,
        settled_paid_cents=3000,
        settled_change_cents=0,
        settled_balance_due_cents=0,
    )
    Order.objects.filter(id=order2.id).update(
        settled_at=start2 + timedelta(hours=3),
        settled_total_cents=1500,
        settled_paid_cents=1500,
        settled_change_cents=0,
        settled_balance_due_cents=0,
    )

    cash_in = Payment.objects.create(
        tenant=tenant,
        order=order1,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=2000,
        reference="rev-cash-in",
    )
    cash_out = Payment.objects.create(
        tenant=tenant,
        order=order1,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=500,
        reference="rev-cash-out",
    )
    card_in = Payment.objects.create(
        tenant=tenant,
        order=order1,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=3000,
        reference="rev-card-in",
    )
    day2_cash_in = Payment.objects.create(
        tenant=tenant,
        order=order2,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1000,
        reference="rev-cash-in-2",
    )
    day2_card_in = Payment.objects.create(
        tenant=tenant,
        order=order2,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1500,
        reference="rev-card-in-2",
    )

    Payment.objects.filter(id__in=[cash_in.id, cash_out.id, card_in.id]).update(
        created_at=start1 + timedelta(hours=1)
    )
    Payment.objects.filter(id__in=[day2_cash_in.id, day2_card_in.id]).update(
        created_at=start2 + timedelta(hours=1)
    )

    resp = client.get(
        "/api/reports/revenue/?start=2026-01-15&end=2026-01-16"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["start"] == "2026-01-15"
    assert data["end"] == "2026-01-16"
    assert data["tenant"] == {"id": tenant.id, "slug": tenant.slug}
    assert len(data["days"]) == 2

    day1_row = data["days"][0]
    assert day1_row["date"] == "2026-01-15"
    assert day1_row["orders_settled_count"] == 1
    assert day1_row["settled_total_cents"] == 3000
    assert day1_row["avg_order_value_cents"] == 3000
    assert day1_row["cash_net_cents"] == 1500
    assert day1_row["card_net_cents"] == 3000

    day2_row = data["days"][1]
    assert day2_row["date"] == "2026-01-16"
    assert day2_row["orders_settled_count"] == 1
    assert day2_row["settled_total_cents"] == 1500
    assert day2_row["avg_order_value_cents"] == 1500
    assert day2_row["cash_net_cents"] == 1000
    assert day2_row["card_net_cents"] == 1500

    assert data["totals"] == {
        "orders_settled_count": 2,
        "settled_total_cents": 4500,
        "avg_order_value_cents": 2250,
        "cash_net_cents": 2500,
        "card_net_cents": 4500,
    }


@pytest.mark.django_db
def test_revenue_report_tenant_isolation(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-rev-a", name="T Rev A")
    tenant_b = Tenant.objects.create(slug="t-rev-b", name="T Rev B")
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
    )

    resp = client.get("/api/reports/revenue/?start=2026-01-15&end=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()

    assert data["totals"] == {
        "orders_settled_count": 0,
        "settled_total_cents": 0,
        "avg_order_value_cents": 0,
        "cash_net_cents": 0,
        "card_net_cents": 0,
    }


@pytest.mark.django_db
def test_revenue_report_validation(django_user_model):
    tenant = Tenant.objects.create(slug="t-rev-val", name="T Rev Val")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get("/api/reports/revenue/?start=2026-01-16")
    assert resp.status_code == 400

    resp = client.get("/api/reports/revenue/?start=2026-01-16&end=2026-01-15")
    assert resp.status_code == 400
