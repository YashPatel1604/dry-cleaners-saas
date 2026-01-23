import pytest
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety


def build_client(*, tenant, user, role) -> APIClient:
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=role,
        is_active=True,
    )
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


@pytest.mark.django_db
def test_reports_unpaid_only_unpaid_and_sorted():
    tenant = Tenant.objects.create(slug="t-unpaid", name="Unpaid")
    admin = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )
    customer = Customer.objects.create(tenant=tenant, name="Customer")

    day = timezone.localdate()
    ts1 = timezone.make_aware(datetime.combine(day, datetime.min.time()))
    ts2 = ts1 + timedelta(hours=1)

    paid_order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        subtotal_cents=900,
        tax_cents=100,
        total_cents=1000,
        paid_cents=1000,
    )

    unpaid_large = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        subtotal_cents=1800,
        tax_cents=200,
        total_cents=2000,
        paid_cents=0,
    )
    Order.objects.filter(id=unpaid_large.id).update(created_at=ts2)

    unpaid_small = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        subtotal_cents=900,
        tax_cents=100,
        total_cents=1000,
        paid_cents=400,
    )
    Order.objects.filter(id=unpaid_small.id).update(created_at=ts1)

    resp = client.get("/api/tenant/reports/unpaid/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["count"] == 2
    assert [row["order_id"] for row in data["results"]] == [
        unpaid_large.id,
        unpaid_small.id,
    ]
    assert all(row["balance_due_cents"] > 0 for row in data["results"])
    assert paid_order.id not in [row["order_id"] for row in data["results"]]


@pytest.mark.django_db
def test_reports_unpaid_access_controls():
    tenant = Tenant.objects.create(slug="t-unpaid-access", name="Unpaid Access")
    admin = get_user_model().objects.create_user(username="admin2", password="pw")
    operator = get_user_model().objects.create_user(username="operator", password="pw")
    outsider = get_user_model().objects.create_user(username="outsider", password="pw")

    admin_client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )
    operator_client = build_client(
        tenant=tenant, user=operator, role=TenantMembership.Role.OPERATOR
    )

    outsider_client = APIClient(raise_request_exception=False)
    outsider_client.force_authenticate(user=outsider)
    outsider_client.credentials(HTTP_X_TENANT=tenant.slug)

    assert admin_client.get("/api/tenant/reports/unpaid/").status_code == 200
    assert operator_client.get("/api/tenant/reports/unpaid/").status_code in (403, 404)
    assert outsider_client.get("/api/tenant/reports/unpaid/").status_code == 404
