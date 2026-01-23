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
def test_reports_range_cap_enforced():
    tenant = Tenant.objects.create(slug="t-range-cap", name="Range Cap")
    admin = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    start = timezone.localdate() - timedelta(days=100)
    end = timezone.localdate()

    resp = client.get(
        f"/api/tenant/reports/range/?start={start.isoformat()}&end={end.isoformat()}"
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_reports_range_includes_zero_days():
    tenant = Tenant.objects.create(slug="t-range-zero", name="Range Zero")
    admin = get_user_model().objects.create_user(username="admin2", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )
    customer = Customer.objects.create(tenant=tenant, name="Customer")

    start = timezone.localdate()
    end = start + timedelta(days=2)

    settled_at = timezone.make_aware(datetime.combine(start, datetime.min.time()))
    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="PICKED_UP",
        subtotal_cents=900,
        tax_cents=100,
        total_cents=1000,
        paid_cents=1000,
        settled_at=settled_at,
        settled_total_cents=1000,
        settled_paid_cents=1000,
        settled_balance_due_cents=0,
    )
    Order.objects.filter(id=order.id).update(created_at=settled_at)

    resp = client.get(
        f"/api/tenant/reports/range/?start={start.isoformat()}&end={end.isoformat()}"
    )
    assert resp.status_code == 200
    series = resp.json()["series"]
    assert [row["date"] for row in series] == [
        start.isoformat(),
        (start + timedelta(days=1)).isoformat(),
        (start + timedelta(days=2)).isoformat(),
    ]
    assert series[1] == {
        "date": (start + timedelta(days=1)).isoformat(),
        "orders_created": 0,
        "orders_settled": 0,
        "net_sales_cents": 0,
        "net_paid_cents": 0,
        "balance_due_cents": 0,
    }


@pytest.mark.django_db
def test_reports_range_query_count(django_assert_num_queries):
    tenant = Tenant.objects.create(slug="t-range-qc", name="Range QC")
    admin = get_user_model().objects.create_user(username="admin-qc", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )
    start = timezone.localdate()
    end = start + timedelta(days=2)

    with django_assert_num_queries(8, exact=False):
        resp = client.get(
            f"/api/tenant/reports/range/?start={start.isoformat()}&end={end.isoformat()}"
        )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_reports_range_data_correctness():
    tenant = Tenant.objects.create(slug="t-range-data", name="Range Data")
    admin = get_user_model().objects.create_user(username="admin3", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )
    customer = Customer.objects.create(tenant=tenant, name="Customer")

    base_day = timezone.localdate()

    day1 = base_day
    day2 = base_day + timedelta(days=1)
    day3 = base_day + timedelta(days=2)

    day1_dt = timezone.make_aware(datetime.combine(day1, datetime.min.time()))
    day2_dt = timezone.make_aware(datetime.combine(day2, datetime.min.time()))
    day3_dt = timezone.make_aware(datetime.combine(day3, datetime.min.time()))

    order1 = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="PICKED_UP",
        subtotal_cents=900,
        tax_cents=100,
        total_cents=1000,
        paid_cents=1000,
        settled_at=day1_dt,
        settled_total_cents=1000,
        settled_paid_cents=900,
        settled_balance_due_cents=100,
    )
    Order.objects.filter(id=order1.id).update(
        created_at=day1_dt
    )

    order2 = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="PICKED_UP",
        subtotal_cents=1800,
        tax_cents=200,
        total_cents=2000,
        paid_cents=2000,
        settled_at=day3_dt,
        settled_total_cents=2000,
        settled_paid_cents=2000,
        settled_balance_due_cents=0,
    )
    Order.objects.filter(id=order2.id).update(
        created_at=day2_dt
    )

    resp = client.get(
        f"/api/tenant/reports/range/?start={day1.isoformat()}&end={day3.isoformat()}"
    )
    assert resp.status_code == 200
    series = resp.json()["series"]

    assert series[0] == {
        "date": day1.isoformat(),
        "orders_created": 1,
        "orders_settled": 1,
        "net_sales_cents": 1000,
        "net_paid_cents": 900,
        "balance_due_cents": 100,
    }
    assert series[1] == {
        "date": day2.isoformat(),
        "orders_created": 1,
        "orders_settled": 0,
        "net_sales_cents": 0,
        "net_paid_cents": 0,
        "balance_due_cents": 0,
    }
    assert series[2] == {
        "date": day3.isoformat(),
        "orders_created": 0,
        "orders_settled": 1,
        "net_sales_cents": 2000,
        "net_paid_cents": 2000,
        "balance_due_cents": 0,
    }
