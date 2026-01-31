from datetime import date, datetime, time, timedelta
import itertools

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
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
        phone=f"7146000{next(_phone_seq):03d}",
    )
    return Order.objects.create(
        tenant=tenant,
        customer=customer,
        status=status,
        due_at=due_at,
    )


@pytest.mark.django_db
def test_workload_report_counts_and_ages(django_user_model):
    tenant = Tenant.objects.create(slug="t-work", name="T Work")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    end = start + timedelta(days=1)

    due_today = create_order(
        tenant=tenant,
        status="RECEIVED",
        due_at=start + timedelta(hours=4),
    )
    overdue = create_order(
        tenant=tenant,
        status="IN_PROGRESS",
        due_at=start - timedelta(days=1),
    )
    ready_unpaid = create_order(
        tenant=tenant,
        status="READY",
        due_at=end + timedelta(days=1),
    )
    completed_unpicked = create_order(
        tenant=tenant,
        status="COMPLETED",
        due_at=end + timedelta(days=2),
    )

    Order.objects.filter(id=ready_unpaid.id).update(settled_balance_due_cents=200)

    Order.objects.filter(id=due_today.id).update(created_at=start + timedelta(hours=2))
    Order.objects.filter(id=overdue.id).update(created_at=start + timedelta(hours=6))
    Order.objects.filter(id=ready_unpaid.id).update(created_at=start + timedelta(hours=8))
    Order.objects.filter(id=completed_unpicked.id).update(created_at=start + timedelta(hours=10))

    resp = client.get(f"/api/reports/workload/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["counts"] == {
        "orders_due_today": 1,
        "orders_overdue": 1,
        "orders_ready_unpaid": 1,
        "orders_completed_unpicked": 1,
    }
    assert data["ready_unpaid_mode"] == "settled_only"
    assert data["avg_age_hours"] == {
        "orders_due_today": 22.0,
        "orders_overdue": 18.0,
        "orders_ready_unpaid": 16.0,
        "orders_completed_unpicked": 14.0,
    }
    assert data["window"]["start"] == start.isoformat()
    assert data["window"]["end"] == end.isoformat()


@pytest.mark.django_db
def test_workload_report_tenant_isolated(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-work-a", name="T Work A")
    tenant_b = Tenant.objects.create(slug="t-work-b", name="T Work B")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant_a, user=user)

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)

    order_b = create_order(
        tenant=tenant_b,
        status="READY",
        due_at=start + timedelta(hours=2),
    )
    Order.objects.filter(id=order_b.id).update(settled_balance_due_cents=100)

    resp = client.get(f"/api/reports/workload/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["counts"] == {
        "orders_due_today": 0,
        "orders_overdue": 0,
        "orders_ready_unpaid": 0,
        "orders_completed_unpicked": 0,
    }
    assert data["avg_age_hours"] == {
        "orders_due_today": 0.0,
        "orders_overdue": 0.0,
        "orders_ready_unpaid": 0.0,
        "orders_completed_unpicked": 0.0,
    }
