from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety


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
        phone=f"7140000{Order.objects.filter(tenant=tenant).count():03d}",
    )
    return Order.objects.create(
        tenant=tenant,
        customer=customer,
        status=status,
        due_at=due_at,
    )


@pytest.mark.django_db
def test_ops_summary_counts(django_user_model):
    tenant = Tenant.objects.create(slug="t-ops", name="T Ops")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, datetime.min.time()), tz)
    end = start + timedelta(days=1)
    before = start - timedelta(days=1)

    create_order(tenant=tenant, status="RECEIVED", due_at=start + timedelta(hours=1))
    create_order(tenant=tenant, status="IN_PROGRESS", due_at=before)

    ready_order = create_order(tenant=tenant, status="READY", due_at=end + timedelta(days=1))
    Order.objects.filter(id=ready_order.id).update(settled_balance_due_cents=0)
    ready_unpaid = create_order(tenant=tenant, status="READY", due_at=end + timedelta(days=2))
    Order.objects.filter(id=ready_unpaid.id).update(settled_balance_due_cents=250)

    create_order(tenant=tenant, status="COMPLETED", due_at=end + timedelta(days=3))

    picked_up = create_order(tenant=tenant, status="PICKED_UP", due_at=end + timedelta(days=4))
    Order.objects.filter(id=picked_up.id).update(picked_up_at=start + timedelta(hours=3))

    settled = create_order(tenant=tenant, status="COMPLETED", due_at=end + timedelta(days=5))
    Order.objects.filter(id=settled.id).update(settled_at=start + timedelta(hours=4))

    resp = client.get(f"/api/reports/ops-summary/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["date"] == "2026-01-15"
    assert data["tenant"] == {"id": tenant.id, "slug": tenant.slug}
    assert set(data.keys()) == {
        "date",
        "tenant",
        "window",
        "counts",
        "ready_unpaid_mode",
    }
    assert data["ready_unpaid_mode"] == "settled_only"
    assert data["counts"] == {
        "orders_due_today": 1,
        "orders_overdue": 1,
        "orders_ready": 2,
        "orders_ready_unpaid": 1,
        "orders_completed_unpicked": 2,
        "orders_picked_up_today": 1,
        "orders_settled_today": 1,
    }
    assert data["window"]["start"] == start.isoformat()
    assert data["window"]["end"] == end.isoformat()


@pytest.mark.django_db
def test_ops_summary_tenant_isolation(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-a-ops", name="T A Ops")
    tenant_b = Tenant.objects.create(slug="t-b-ops", name="T B Ops")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant_a, user=user)

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, datetime.min.time()), tz)

    order_b = create_order(tenant=tenant_b, status="READY", due_at=start)
    Order.objects.filter(id=order_b.id).update(settled_balance_due_cents=100)

    resp = client.get(f"/api/reports/ops-summary/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["tenant"] == {"id": tenant_a.id, "slug": tenant_a.slug}
    assert data["counts"] == {
        "orders_due_today": 0,
        "orders_overdue": 0,
        "orders_ready": 0,
        "orders_ready_unpaid": 0,
        "orders_completed_unpicked": 0,
        "orders_picked_up_today": 0,
        "orders_settled_today": 0,
    }


@pytest.mark.django_db
def test_ops_summary_default_date(django_user_model):
    tenant = Tenant.objects.create(slug="t-ops-default", name="T Ops Default")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    today = timezone.localdate().isoformat()
    resp = client.get("/api/reports/ops-summary/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == today
