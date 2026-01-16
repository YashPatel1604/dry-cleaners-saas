from datetime import date, datetime, time, timedelta
import csv
import io
import itertools

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
from payments.models import Adjustment, Payment
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
        phone=f"7147000{next(_phone_seq):03d}",
    )


def create_order(*, tenant, customer: Customer, status: str, due_at=None) -> Order:
    return Order.objects.create(
        tenant=tenant,
        customer=customer,
        status=status,
        due_at=due_at,
    )


def seed_tenant_activity(*, tenant, day: date):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)

    customer = create_customer(tenant=tenant, name="Patel")
    order = create_order(
        tenant=tenant,
        customer=customer,
        status="COMPLETED",
        due_at=start + timedelta(hours=2),
    )
    Order.objects.filter(id=order.id).update(
        settled_at=start + timedelta(hours=1),
        settled_total_cents=1200,
        settled_paid_cents=1500,
        settled_change_cents=300,
        settled_balance_due_cents=0,
        subtotal_cents=1000,
        tax_cents=200,
    )

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=800,
        reference="seed-cash-in",
        created_at=start + timedelta(hours=3),
    )
    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=200,
        reference="seed-cash-out",
        note="Refund payout",
        created_at=start + timedelta(hours=4),
    )
    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=500,
        reference="seed-card-in",
        created_at=start + timedelta(hours=5),
    )

    Adjustment.objects.create(
        tenant=tenant,
        order=order,
        status=Adjustment.Status.APPLIED,
        direction=Adjustment.Direction.IN,
        amount_cents=50,
        reference="seed-adj-in",
        created_at=start + timedelta(hours=6),
    )

    ready_unpaid = create_order(
        tenant=tenant,
        customer=customer,
        status="READY",
        due_at=start + timedelta(hours=8),
    )
    Order.objects.filter(id=ready_unpaid.id).update(settled_balance_due_cents=100)


@pytest.mark.django_db
def test_report_schema_daily_cash_close(django_user_model):
    tenant = Tenant.objects.create(slug="t-schema-dcc", name="T Schema DCC")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    day = date(2026, 1, 15)
    resp = client.get(f"/api/reports/daily-cash-close/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert set(data.keys()) == {
        "date",
        "tenant",
        "window",
        "cash",
        "card",
        "adjustments",
        "settlement",
    }
    assert isinstance(data["date"], str)
    assert isinstance(data["tenant"]["id"], int)
    assert isinstance(data["tenant"]["slug"], str)
    assert isinstance(data["window"]["start"], str)
    assert isinstance(data["window"]["end"], str)
    for key in ("cash", "card", "adjustments"):
        assert set(data[key].keys()) == {"in_cents", "out_cents", "net_cents"}
        assert isinstance(data[key]["in_cents"], int)
        assert isinstance(data[key]["out_cents"], int)
        assert isinstance(data[key]["net_cents"], int)
    assert set(data["settlement"].keys()) == {
        "orders_settled_count",
        "settled_total_cents",
        "settled_paid_cents",
        "settled_change_cents",
        "settled_balance_due_cents",
    }


@pytest.mark.django_db
def test_report_schema_daily_cash_close_range(django_user_model):
    tenant = Tenant.objects.create(slug="t-schema-dccr", name="T Schema DCCR")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get(
        "/api/reports/daily-cash-close/range/?start=2026-01-15&end=2026-01-16"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert set(data[0].keys()) == {
        "date",
        "tenant",
        "window",
        "cash",
        "card",
        "adjustments",
        "settlement",
    }


@pytest.mark.django_db
def test_report_schema_daily_cash_close_csv(django_user_model):
    tenant = Tenant.objects.create(slug="t-schema-csv", name="T Schema CSV")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get("/api/reports/daily-cash-close.csv?date=2026-01-15")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    reader = csv.reader(io.StringIO(resp.content.decode()))
    header = next(reader)
    assert header == [
        "date",
        "tenant_id",
        "tenant_slug",
        "window_start",
        "window_end",
        "cash_in_cents",
        "cash_out_cents",
        "cash_net_cents",
        "card_in_cents",
        "card_out_cents",
        "card_net_cents",
        "adjustments_in_cents",
        "adjustments_out_cents",
        "adjustments_net_cents",
        "settlement_orders_settled_count",
        "settlement_settled_total_cents",
        "settlement_settled_paid_cents",
        "settlement_settled_change_cents",
        "settlement_settled_balance_due_cents",
    ]


@pytest.mark.django_db
def test_report_schema_cash_drawer(django_user_model):
    tenant = Tenant.objects.create(slug="t-schema-cd", name="T Schema CD")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get("/api/reports/cash-drawer/?date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"date", "tenant", "window", "cash", "breakdown", "notes"}
    assert isinstance(data["cash"]["in_cents"], int)
    assert isinstance(data["breakdown"]["other_cash_out_cents"], int)
    assert isinstance(data["notes"], list)


@pytest.mark.django_db
def test_report_schema_ops_summary(django_user_model):
    tenant = Tenant.objects.create(slug="t-schema-ops", name="T Schema OPS")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get("/api/reports/ops-summary/?date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"date", "tenant", "window", "counts", "ready_unpaid_mode"}
    assert data["ready_unpaid_mode"] == "settled_only"
    assert isinstance(data["counts"]["orders_ready_unpaid"], int)


@pytest.mark.django_db
def test_report_schema_revenue(django_user_model):
    tenant = Tenant.objects.create(slug="t-schema-rev", name="T Schema REV")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get("/api/reports/revenue/?start=2026-01-15&end=2026-01-16")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"start", "end", "tenant", "window", "days", "totals"}
    assert len(data["days"]) == 2
    day = data["days"][0]
    assert set(day.keys()) == {
        "date",
        "orders_settled_count",
        "settled_total_cents",
        "avg_order_value_cents",
        "cash_net_cents",
        "card_net_cents",
    }
    assert isinstance(data["totals"]["settled_total_cents"], int)


@pytest.mark.django_db
def test_report_schema_settlement_breakdown(django_user_model):
    tenant = Tenant.objects.create(slug="t-schema-sb", name="T Schema SB")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get(
        "/api/reports/settlement-breakdown/?start=2026-01-15&end=2026-01-15"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {
        "start",
        "end",
        "tenant",
        "window",
        "subtotal_cents",
        "tax_cents",
        "total_cents",
        "adjustments_in_cents",
        "adjustments_out_cents",
        "adjustments_net_cents",
        "paid_cents",
        "change_cents",
        "balance_due_cents",
    }


@pytest.mark.django_db
def test_report_schema_top_customers(django_user_model):
    tenant = Tenant.objects.create(slug="t-schema-top", name="T Schema TOP")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    day = date(2026, 1, 15)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)

    customer = create_customer(tenant=tenant, name="Alice")
    order = create_order(tenant=tenant, customer=customer, status="COMPLETED")
    Order.objects.filter(id=order.id).update(
        settled_at=start + timedelta(hours=1),
        settled_total_cents=1200,
    )

    resp = client.get(
        "/api/reports/customers/top/?start=2026-01-15&end=2026-01-15"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    entry = data["results"][0]
    assert set(entry.keys()) == {
        "customer",
        "orders_count",
        "settled_total_cents",
        "last_seen_at",
    }
    assert isinstance(entry["customer"]["id"], int)


@pytest.mark.django_db
def test_report_schema_workload(django_user_model):
    tenant = Tenant.objects.create(slug="t-schema-work", name="T Schema WORK")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get("/api/reports/workload/?date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {
        "date",
        "tenant",
        "window",
        "counts",
        "avg_age_hours",
        "ready_unpaid_mode",
    }
    assert isinstance(data["avg_age_hours"]["orders_overdue"], float)


@pytest.mark.django_db
def test_report_tenant_isolation_all_endpoints(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-iso-a", name="T Iso A")
    tenant_b = Tenant.objects.create(slug="t-iso-b", name="T Iso B")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant_a, user=user)

    day1 = date(2026, 1, 15)
    day2 = date(2026, 1, 16)
    seed_tenant_activity(tenant=tenant_b, day=day1)

    resp = client.get(f"/api/reports/daily-cash-close/?date={day1.isoformat()}")
    data = resp.json()
    assert data["cash"]["net_cents"] == 0
    assert data["settlement"]["orders_settled_count"] == 0

    resp = client.get(
        f"/api/reports/daily-cash-close/range/?start={day1.isoformat()}&end={day2.isoformat()}"
    )
    data = resp.json()
    assert len(data) == 2
    assert all(item["cash"]["net_cents"] == 0 for item in data)

    resp = client.get(f"/api/reports/cash-drawer/?date={day1.isoformat()}")
    data = resp.json()
    assert data["cash"]["net_cents"] == 0
    assert data["breakdown"]["other_cash_out_cents"] == 0

    resp = client.get(f"/api/reports/ops-summary/?date={day1.isoformat()}")
    data = resp.json()
    assert data["counts"]["orders_ready_unpaid"] == 0

    resp = client.get(
        f"/api/reports/revenue/?start={day1.isoformat()}&end={day2.isoformat()}"
    )
    data = resp.json()
    assert data["totals"]["settled_total_cents"] == 0

    resp = client.get(
        f"/api/reports/settlement-breakdown/?start={day1.isoformat()}&end={day2.isoformat()}"
    )
    data = resp.json()
    assert data["total_cents"] == 0

    resp = client.get(
        f"/api/reports/customers/top/?start={day1.isoformat()}&end={day2.isoformat()}"
    )
    data = resp.json()
    assert data["results"] == []

    resp = client.get(f"/api/reports/workload/?date={day1.isoformat()}")
    data = resp.json()
    assert data["counts"]["orders_due_today"] == 0

    resp = client.get(f"/api/reports/daily-cash-close.csv?date={day1.isoformat()}")
    lines = resp.content.decode().strip().splitlines()
    assert len(lines) == 2
    csv_values = lines[1].split(",")
    numeric_tail = [int(v) for v in csv_values[5:]]
    assert all(v == 0 for v in numeric_tail)


@pytest.mark.django_db
def test_report_query_counts_for_range_endpoints(django_user_model):
    tenant = Tenant.objects.create(slug="t-qc-reports", name="T QC Reports")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    with CaptureQueriesContext(connection) as ctx:
        client.get(
            "/api/reports/daily-cash-close/range/?start=2026-01-15&end=2026-01-16"
        )
    assert len(ctx) <= 8

    with CaptureQueriesContext(connection) as ctx:
        client.get("/api/reports/revenue/?start=2026-01-15&end=2026-01-16")
    assert len(ctx) <= 4

    with CaptureQueriesContext(connection) as ctx:
        client.get(
            "/api/reports/settlement-breakdown/?start=2026-01-15&end=2026-01-16"
        )
    assert len(ctx) <= 4

    with CaptureQueriesContext(connection) as ctx:
        client.get(
            "/api/reports/customers/top/?start=2026-01-15&end=2026-01-16&limit=20"
        )
    assert len(ctx) <= 3
