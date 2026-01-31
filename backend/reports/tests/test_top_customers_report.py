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


def create_customer(*, tenant, name: str) -> Customer:
    return Customer.objects.create(
        tenant=tenant,
        name=name,
        phone=f"7145000{next(_phone_seq):03d}",
    )


def create_order(*, tenant, customer: Customer) -> Order:
    return Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="COMPLETED",
        due_at=timezone.now(),
    )


@pytest.mark.django_db
def test_top_customers_report_range(django_user_model):
    tenant = Tenant.objects.create(slug="t-top", name="T Top")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    day1 = date(2026, 1, 15)
    day2 = date(2026, 1, 16)
    tz = timezone.get_current_timezone()
    start1 = timezone.make_aware(datetime.combine(day1, time.min), tz)
    start2 = timezone.make_aware(datetime.combine(day2, time.min), tz)

    customer_a = create_customer(tenant=tenant, name="Alice")
    customer_b = create_customer(tenant=tenant, name="Bob")

    order_a1 = create_order(tenant=tenant, customer=customer_a)
    order_a2 = create_order(tenant=tenant, customer=customer_a)
    order_b1 = create_order(tenant=tenant, customer=customer_b)

    Order.objects.filter(id=order_a1.id).update(
        settled_at=start1 + timedelta(hours=1),
        settled_total_cents=3000,
    )
    Order.objects.filter(id=order_a2.id).update(
        settled_at=start2 + timedelta(hours=2),
        settled_total_cents=1500,
    )
    Order.objects.filter(id=order_b1.id).update(
        settled_at=start1 + timedelta(hours=3),
        settled_total_cents=2000,
    )

    resp = client.get(
        "/api/reports/customers/top/?start=2026-01-15&end=2026-01-16&limit=20"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["start"] == "2026-01-15"
    assert data["end"] == "2026-01-16"
    assert data["tenant"] == {"id": tenant.id, "slug": tenant.slug}
    assert len(data["results"]) == 2

    first = data["results"][0]
    assert first["customer"]["id"] == customer_a.id
    assert first["orders_count"] == 2
    assert first["settled_total_cents"] == 4500
    expected_last_seen = (start2 + timedelta(hours=2)).astimezone(timezone.UTC)
    assert first["last_seen_at"] == expected_last_seen.isoformat()

    second = data["results"][1]
    assert second["customer"]["id"] == customer_b.id
    assert second["orders_count"] == 1
    assert second["settled_total_cents"] == 2000
    expected_last_seen_b = (start1 + timedelta(hours=3)).astimezone(timezone.UTC)
    assert second["last_seen_at"] == expected_last_seen_b.isoformat()


@pytest.mark.django_db
def test_top_customers_report_tenant_isolated(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-top-a", name="T Top A")
    tenant_b = Tenant.objects.create(slug="t-top-b", name="T Top B")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant_a, user=user)

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)

    customer_b = create_customer(tenant=tenant_b, name="B1")
    order_b = create_order(tenant=tenant_b, customer=customer_b)
    Order.objects.filter(id=order_b.id).update(
        settled_at=start + timedelta(hours=1),
        settled_total_cents=999,
    )

    resp = client.get(
        "/api/reports/customers/top/?start=2026-01-15&end=2026-01-15"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []


@pytest.mark.django_db
def test_top_customers_report_validation(django_user_model):
    tenant = Tenant.objects.create(slug="t-top-val", name="T Top Val")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get("/api/reports/customers/top/?start=2026-01-15")
    assert resp.status_code == 400

    resp = client.get(
        "/api/reports/customers/top/?start=2026-01-16&end=2026-01-15"
    )
    assert resp.status_code == 400
