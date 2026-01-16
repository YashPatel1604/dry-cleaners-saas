from datetime import datetime, time, timedelta
import itertools
import csv
import io

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


def create_order(*, tenant) -> Order:
    phone = f"7140000{next(_phone_seq):03d}"
    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone=phone,
    )
    return Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        due_at=timezone.now(),
    )


@pytest.mark.django_db
def test_daily_cash_close_report_sums(django_user_model):
    tenant = Tenant.objects.create(slug="t-reports", name="T Reports")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = create_order(tenant=tenant)

    cash_in = Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1000,
        reference="cash-in",
    )
    cash_out = Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=200,
        reference="cash-out",
    )
    card_in = Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=500,
        reference="card-in",
    )
    adjustment_in = Adjustment.objects.create(
        tenant=tenant,
        order=order,
        status=Adjustment.Status.APPLIED,
        direction=Adjustment.Direction.IN,
        amount_cents=50,
        reference="adj-in",
    )

    day = timezone.localdate()
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    inside = start + timedelta(hours=2)

    Payment.objects.filter(id__in=[cash_in.id, cash_out.id, card_in.id]).update(
        created_at=inside
    )
    Adjustment.objects.filter(id=adjustment_in.id).update(created_at=inside)
    Order.objects.filter(id=order.id).update(
        settled_at=inside,
        settled_total_cents=1200,
        settled_paid_cents=1500,
        settled_change_cents=300,
        settled_balance_due_cents=0,
    )

    resp = client.get(f"/api/reports/daily-cash-close/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    expected_keys = {
        "date",
        "tenant",
        "window",
        "cash",
        "card",
        "adjustments",
        "settlement",
    }
    assert set(data.keys()) == expected_keys

    assert data["cash"] == {"in_cents": 1000, "out_cents": 200, "net_cents": 800}
    assert data["card"] == {"in_cents": 500, "out_cents": 0, "net_cents": 500}
    assert data["adjustments"] == {
        "in_cents": 50,
        "out_cents": 0,
        "net_cents": 50,
    }
    assert data["settlement"] == {
        "orders_settled_count": 1,
        "settled_total_cents": 1200,
        "settled_paid_cents": 1500,
        "settled_change_cents": 300,
        "settled_balance_due_cents": 0,
    }


@pytest.mark.django_db
def test_daily_cash_close_report_tenant_isolated(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-a", name="Tenant A")
    tenant_b = Tenant.objects.create(slug="t-b", name="Tenant B")
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

    day = timezone.localdate()
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    Payment.objects.filter(id=payment_b.id).update(created_at=start + timedelta(hours=1))

    resp = client.get(f"/api/reports/daily-cash-close/?date={day.isoformat()}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["tenant"] == {"id": tenant_a.id, "slug": tenant_a.slug}
    assert data["cash"] == {"in_cents": 0, "out_cents": 0, "net_cents": 0}
    assert data["card"] == {"in_cents": 0, "out_cents": 0, "net_cents": 0}
    assert data["adjustments"] == {
        "in_cents": 0,
        "out_cents": 0,
        "net_cents": 0,
    }
    assert data["settlement"] == {
        "orders_settled_count": 0,
        "settled_total_cents": 0,
        "settled_paid_cents": 0,
        "settled_change_cents": 0,
        "settled_balance_due_cents": 0,
    }


@pytest.mark.django_db
def test_daily_cash_close_range_report_sums(django_user_model):
    tenant = Tenant.objects.create(slug="t-range", name="T Range")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    day1 = timezone.localdate()
    day2 = day1 + timedelta(days=1)
    tz = timezone.get_current_timezone()
    start1 = timezone.make_aware(datetime.combine(day1, time.min), tz)
    start2 = timezone.make_aware(datetime.combine(day2, time.min), tz)

    order1 = create_order(tenant=tenant)
    order2 = create_order(tenant=tenant)

    p1_cash_in = Payment.objects.create(
        tenant=tenant,
        order=order1,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1000,
        reference="range-cash-in",
    )
    p1_card_in = Payment.objects.create(
        tenant=tenant,
        order=order1,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=200,
        reference="range-card-in",
    )
    adj1_out = Adjustment.objects.create(
        tenant=tenant,
        order=order1,
        status=Adjustment.Status.APPLIED,
        direction=Adjustment.Direction.OUT,
        amount_cents=50,
        reference="range-adj-out",
    )

    p2_cash_out = Payment.objects.create(
        tenant=tenant,
        order=order2,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=300,
        reference="range-cash-out",
    )
    p2_card_in = Payment.objects.create(
        tenant=tenant,
        order=order2,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=400,
        reference="range-card-in-2",
    )
    adj2_in = Adjustment.objects.create(
        tenant=tenant,
        order=order2,
        status=Adjustment.Status.APPLIED,
        direction=Adjustment.Direction.IN,
        amount_cents=25,
        reference="range-adj-in",
    )

    Payment.objects.filter(id__in=[p1_cash_in.id, p1_card_in.id]).update(
        created_at=start1 + timedelta(hours=1)
    )
    Adjustment.objects.filter(id=adj1_out.id).update(
        created_at=start1 + timedelta(hours=2)
    )
    Order.objects.filter(id=order1.id).update(
        settled_at=start1 + timedelta(hours=3),
        settled_total_cents=1200,
        settled_paid_cents=1200,
        settled_change_cents=0,
        settled_balance_due_cents=0,
    )

    Payment.objects.filter(id__in=[p2_cash_out.id, p2_card_in.id]).update(
        created_at=start2 + timedelta(hours=1)
    )
    Adjustment.objects.filter(id=adj2_in.id).update(
        created_at=start2 + timedelta(hours=2)
    )
    Order.objects.filter(id=order2.id).update(
        settled_at=start2 + timedelta(hours=3),
        settled_total_cents=700,
        settled_paid_cents=700,
        settled_change_cents=0,
        settled_balance_due_cents=0,
    )

    resp = client.get(
        "/api/reports/daily-cash-close/range/"
        f"?start={day1.isoformat()}&end={day2.isoformat()}"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    assert data[0]["date"] == day1.isoformat()
    assert data[0]["cash"] == {"in_cents": 1000, "out_cents": 0, "net_cents": 1000}
    assert data[0]["card"] == {"in_cents": 200, "out_cents": 0, "net_cents": 200}
    assert data[0]["adjustments"] == {"in_cents": 0, "out_cents": 50, "net_cents": -50}
    assert data[0]["settlement"] == {
        "orders_settled_count": 1,
        "settled_total_cents": 1200,
        "settled_paid_cents": 1200,
        "settled_change_cents": 0,
        "settled_balance_due_cents": 0,
    }

    assert data[1]["date"] == day2.isoformat()
    assert data[1]["cash"] == {"in_cents": 0, "out_cents": 300, "net_cents": -300}
    assert data[1]["card"] == {"in_cents": 400, "out_cents": 0, "net_cents": 400}
    assert data[1]["adjustments"] == {"in_cents": 25, "out_cents": 0, "net_cents": 25}
    assert data[1]["settlement"] == {
        "orders_settled_count": 1,
        "settled_total_cents": 700,
        "settled_paid_cents": 700,
        "settled_change_cents": 0,
        "settled_balance_due_cents": 0,
    }


@pytest.mark.django_db
def test_daily_cash_close_range_report_tenant_isolated(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-a-range", name="Tenant A Range")
    tenant_b = Tenant.objects.create(slug="t-b-range", name="Tenant B Range")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant_a, user=user)

    day1 = timezone.localdate()
    day2 = day1 + timedelta(days=1)
    tz = timezone.get_current_timezone()
    start1 = timezone.make_aware(datetime.combine(day1, time.min), tz)
    start2 = timezone.make_aware(datetime.combine(day2, time.min), tz)

    order_b1 = create_order(tenant=tenant_b)
    order_b2 = create_order(tenant=tenant_b)

    payment_b1 = Payment.objects.create(
        tenant=tenant_b,
        order=order_b1,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=111,
        reference="range-b1",
    )
    payment_b2 = Payment.objects.create(
        tenant=tenant_b,
        order=order_b2,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=222,
        reference="range-b2",
    )

    Payment.objects.filter(id=payment_b1.id).update(created_at=start1 + timedelta(hours=1))
    Payment.objects.filter(id=payment_b2.id).update(created_at=start2 + timedelta(hours=1))

    resp = client.get(
        "/api/reports/daily-cash-close/range/"
        f"?start={day1.isoformat()}&end={day2.isoformat()}"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    for item in data:
        assert item["tenant"] == {"id": tenant_a.id, "slug": tenant_a.slug}
        assert item["cash"] == {"in_cents": 0, "out_cents": 0, "net_cents": 0}
        assert item["card"] == {"in_cents": 0, "out_cents": 0, "net_cents": 0}
        assert item["adjustments"] == {"in_cents": 0, "out_cents": 0, "net_cents": 0}
        assert item["settlement"] == {
            "orders_settled_count": 0,
            "settled_total_cents": 0,
            "settled_paid_cents": 0,
            "settled_change_cents": 0,
            "settled_balance_due_cents": 0,
        }


def parse_csv_response(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def parse_csv_header(content: str) -> list[str]:
    reader = csv.reader(io.StringIO(content))
    return next(reader)


@pytest.mark.django_db
def test_daily_cash_close_report_query_count(django_user_model):
    tenant = Tenant.objects.create(slug="t-qc", name="T QC")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    day = timezone.localdate()
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)

    orders = [create_order(tenant=tenant) for _ in range(10)]
    payments = []
    adjustments = []

    for idx, order in enumerate(orders):
        payments.append(
            Payment.objects.create(
                tenant=tenant,
                order=order,
                method=Payment.Method.CASH if idx % 2 == 0 else Payment.Method.CARD,
                status=Payment.Status.CAPTURED,
                direction=Payment.Direction.IN,
                amount_cents=100 + idx,
                reference=f"qc-pay-{idx}",
            )
        )
        adjustments.append(
            Adjustment.objects.create(
                tenant=tenant,
                order=order,
                status=Adjustment.Status.APPLIED,
                direction=Adjustment.Direction.OUT,
                amount_cents=5,
                reference=f"qc-adj-{idx}",
            )
        )

    Payment.objects.filter(id__in=[p.id for p in payments]).update(
        created_at=start + timedelta(hours=1)
    )
    Adjustment.objects.filter(id__in=[a.id for a in adjustments]).update(
        created_at=start + timedelta(hours=1)
    )
    Order.objects.filter(id__in=[o.id for o in orders]).update(
        settled_at=start + timedelta(hours=2),
        settled_total_cents=500,
        settled_paid_cents=500,
        settled_change_cents=0,
        settled_balance_due_cents=0,
    )

    with CaptureQueriesContext(connection) as ctx:
        resp = client.get(f"/api/reports/daily-cash-close/?date={day.isoformat()}")

    assert resp.status_code == 200
    assert len(ctx) <= 6


@pytest.mark.django_db
def test_daily_cash_close_csv_single_day_matches_json(django_user_model):
    tenant = Tenant.objects.create(slug="t-csv", name="T CSV")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = create_order(tenant=tenant)
    payment = Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1234,
        reference="csv-cash",
    )

    day = timezone.localdate()
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    Payment.objects.filter(id=payment.id).update(created_at=start + timedelta(hours=1))
    Order.objects.filter(id=order.id).update(
        settled_at=start + timedelta(hours=2),
        settled_total_cents=1234,
        settled_paid_cents=1234,
        settled_change_cents=0,
        settled_balance_due_cents=0,
    )

    csv_resp = client.get(f"/api/reports/daily-cash-close.csv?date={day.isoformat()}")
    assert csv_resp.status_code == 200
    assert csv_resp["Content-Type"].startswith("text/csv")
    header = parse_csv_header(csv_resp.content.decode())
    rows = parse_csv_response(csv_resp.content.decode())
    assert len(rows) == 1

    json_resp = client.get(f"/api/reports/daily-cash-close/?date={day.isoformat()}")
    assert json_resp.status_code == 200
    report = json_resp.json()

    row = rows[0]
    assert row["date"] == report["date"]
    assert row["tenant_id"] == str(report["tenant"]["id"])
    assert row["tenant_slug"] == report["tenant"]["slug"]
    assert row["cash_in_cents"] == str(report["cash"]["in_cents"])
    assert row["cash_out_cents"] == str(report["cash"]["out_cents"])
    assert row["cash_net_cents"] == str(report["cash"]["net_cents"])
    assert row["card_in_cents"] == str(report["card"]["in_cents"])
    assert row["card_out_cents"] == str(report["card"]["out_cents"])
    assert row["card_net_cents"] == str(report["card"]["net_cents"])
    assert row["adjustments_in_cents"] == str(report["adjustments"]["in_cents"])
    assert row["adjustments_out_cents"] == str(report["adjustments"]["out_cents"])
    assert row["adjustments_net_cents"] == str(report["adjustments"]["net_cents"])
    assert row["settlement_orders_settled_count"] == str(
        report["settlement"]["orders_settled_count"]
    )
    assert row["settlement_settled_total_cents"] == str(
        report["settlement"]["settled_total_cents"]
    )
    assert row["settlement_settled_paid_cents"] == str(
        report["settlement"]["settled_paid_cents"]
    )
    assert row["settlement_settled_change_cents"] == str(
        report["settlement"]["settled_change_cents"]
    )
    assert row["settlement_settled_balance_due_cents"] == str(
        report["settlement"]["settled_balance_due_cents"]
    )
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
def test_daily_cash_close_csv_range_matches_json(django_user_model):
    tenant = Tenant.objects.create(slug="t-csv-range", name="T CSV Range")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    day1 = timezone.localdate()
    day2 = day1 + timedelta(days=1)
    tz = timezone.get_current_timezone()
    start1 = timezone.make_aware(datetime.combine(day1, time.min), tz)
    start2 = timezone.make_aware(datetime.combine(day2, time.min), tz)

    order1 = create_order(tenant=tenant)
    order2 = create_order(tenant=tenant)

    p1 = Payment.objects.create(
        tenant=tenant,
        order=order1,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=250,
        reference="csv-range-1",
    )
    p2 = Payment.objects.create(
        tenant=tenant,
        order=order2,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.OUT,
        amount_cents=75,
        reference="csv-range-2",
    )

    Payment.objects.filter(id=p1.id).update(created_at=start1 + timedelta(hours=1))
    Payment.objects.filter(id=p2.id).update(created_at=start2 + timedelta(hours=1))

    csv_resp = client.get(
        "/api/reports/daily-cash-close.csv"
        f"?start={day1.isoformat()}&end={day2.isoformat()}"
    )
    assert csv_resp.status_code == 200
    assert csv_resp["Content-Type"].startswith("text/csv")
    header = parse_csv_header(csv_resp.content.decode())
    rows = parse_csv_response(csv_resp.content.decode())
    assert len(rows) == 2

    json_resp = client.get(
        "/api/reports/daily-cash-close/range/"
        f"?start={day1.isoformat()}&end={day2.isoformat()}"
    )
    assert json_resp.status_code == 200
    reports = json_resp.json()
    assert len(reports) == 2
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

    for row, report in zip(rows, reports, strict=True):
        assert row["date"] == report["date"]
        assert row["cash_in_cents"] == str(report["cash"]["in_cents"])
        assert row["cash_out_cents"] == str(report["cash"]["out_cents"])
        assert row["cash_net_cents"] == str(report["cash"]["net_cents"])
        assert row["card_in_cents"] == str(report["card"]["in_cents"])
        assert row["card_out_cents"] == str(report["card"]["out_cents"])
        assert row["card_net_cents"] == str(report["card"]["net_cents"])
        assert row["adjustments_in_cents"] == str(report["adjustments"]["in_cents"])
        assert row["adjustments_out_cents"] == str(report["adjustments"]["out_cents"])
        assert row["adjustments_net_cents"] == str(report["adjustments"]["net_cents"])
        assert row["settlement_orders_settled_count"] == str(
            report["settlement"]["orders_settled_count"]
        )
        assert row["settlement_settled_total_cents"] == str(
            report["settlement"]["settled_total_cents"]
        )
        assert row["settlement_settled_paid_cents"] == str(
            report["settlement"]["settled_paid_cents"]
        )
        assert row["settlement_settled_change_cents"] == str(
            report["settlement"]["settled_change_cents"]
        )
        assert row["settlement_settled_balance_due_cents"] == str(
            report["settlement"]["settled_balance_due_cents"]
        )
