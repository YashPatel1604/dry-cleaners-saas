import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
from payments.models import Payment
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
def test_reports_summary_empty_day():
    tenant = Tenant.objects.create(slug="t-summary-empty", name="Summary Empty")
    admin = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    resp = client.get("/api/tenant/reports/summary/?date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["orders"] == {
        "created_count": 0,
        "settled_count": 0,
        "open_count": 0,
        "unpaid_count": 0,
    }
    assert data["money"] == {
        "gross_sales_cents": 0,
        "discounts_cents": 0,
        "tax_cents": 0,
        "net_sales_cents": 0,
        "net_paid_cents": 0,
        "balance_due_cents": 0,
        "change_due_cents": 0,
    }
    assert data["payments"]["by_method"] == [
        {"method": "CASH", "amount_cents": 0},
        {"method": "CARD", "amount_cents": 0},
        {"method": "OTHER", "amount_cents": 0},
    ]


@pytest.mark.django_db
def test_reports_summary_query_count(django_assert_num_queries):
    tenant = Tenant.objects.create(slug="t-summary-qc", name="Summary QC")
    admin = get_user_model().objects.create_user(username="admin-qc", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    with django_assert_num_queries(10, exact=False):
        resp = client.get("/api/tenant/reports/summary/?date=2026-01-15")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_reports_summary_access_controls():
    tenant = Tenant.objects.create(slug="t-summary-access", name="Summary Access")
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

    assert admin_client.get("/api/tenant/reports/summary/").status_code == 200
    assert operator_client.get("/api/tenant/reports/summary/").status_code in (403, 404)
    assert outsider_client.get("/api/tenant/reports/summary/").status_code == 404


@pytest.mark.django_db
def test_reports_summary_money_uses_receipt_paths():
    tenant = Tenant.objects.create(slug="t-summary-money", name="Summary Money")
    admin = get_user_model().objects.create_user(username="admin3", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    now = timezone.now()
    customer = Customer.objects.create(tenant=tenant, name="Test Customer")

    settled_order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="PICKED_UP",
        subtotal_cents=900,
        tax_cents=100,
        total_cents=1000,
        paid_cents=1000,
        settled_at=now,
        settled_total_cents=1000,
        settled_paid_cents=1000,
        settled_change_cents=0,
        settled_balance_due_cents=0,
    )

    open_partial = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        subtotal_cents=900,
        tax_cents=100,
        total_cents=1000,
        paid_cents=400,
    )

    open_overpaid = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        subtotal_cents=900,
        tax_cents=100,
        total_cents=1000,
        paid_cents=1200,
    )

    Payment.objects.create(
        tenant=tenant,
        order=settled_order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1000,
    )
    Payment.objects.create(
        tenant=tenant,
        order=open_partial,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=400,
    )
    Payment.objects.create(
        tenant=tenant,
        order=open_overpaid,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1200,
    )

    resp = client.get(f"/api/tenant/reports/summary/?date={timezone.localdate().isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["orders"] == {
        "created_count": 3,
        "settled_count": 1,
        "open_count": 2,
        "unpaid_count": 1,
    }

    assert data["money"] == {
        "gross_sales_cents": 3000,
        "discounts_cents": 0,
        "tax_cents": 300,
        "net_sales_cents": 3000,
        "net_paid_cents": 2600,
        "balance_due_cents": 600,
        "change_due_cents": 200,
    }

    assert data["payments"]["by_method"] == [
        {"method": "CASH", "amount_cents": 1400},
        {"method": "CARD", "amount_cents": 1200},
        {"method": "OTHER", "amount_cents": 0},
    ]
