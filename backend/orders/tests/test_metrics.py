from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
from customers.models import Customer
from orders.models import Order
from payments.models import Payment

User = get_user_model()

pytestmark = pytest.mark.operator_safety


class TestOrderMetrics(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(name="T1", slug="t1")
        self.other_tenant = Tenant.objects.create(name="T2", slug="t2")

        self.user = User.objects.create_user(username="admin", password="pass")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantMembership.Role.OWNER_ADMIN,
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT=self.tenant.slug)

        self.customer = Customer.objects.create(
            tenant=self.tenant, name="Patel", phone="7140000000"
        )
        self.customer2 = Customer.objects.create(
            tenant=self.other_tenant, name="Other", phone="9490000000"
        )

        # Orders in-tenant
        self.o_ready = Order.objects.create(
            tenant=self.tenant, customer=self.customer, status="READY",
            settled_balance_due_cents=0
        )
        self.o_ready_unpaid = Order.objects.create(
            tenant=self.tenant, customer=self.customer, status="READY",
            settled_balance_due_cents=500
        )
        self.o_in_progress = Order.objects.create(
            tenant=self.tenant, customer=self.customer, status="IN_PROGRESS"
        )
        self.o_cancelled = Order.objects.create(
            tenant=self.tenant, customer=self.customer, status="CANCELLED"
        )

        # Cross-tenant order (must not affect metrics)
        Order.objects.create(
            tenant=self.other_tenant, customer=self.customer2, status="READY",
            settled_balance_due_cents=999
        )

        now = timezone.now()

        # Payments today (in-tenant)
        self.p1 = Payment.objects.create(
            tenant=self.tenant,
            order=self.o_ready,
            method=Payment.Method.CARD,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.IN,
            amount_cents=2000,
            reference="p1",
        )
        self.p2 = Payment.objects.create(
            tenant=self.tenant,
            order=self.o_ready,
            method=Payment.Method.CASH,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.OUT,
            amount_cents=300,
            reference="p2",
        )

        # Payment yesterday (should NOT count)
        p_old = Payment.objects.create(
            tenant=self.tenant,
            order=self.o_ready,
            method=Payment.Method.CARD,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.IN,
            amount_cents=9999,
            reference="old",
        )
        Payment.objects.filter(id=p_old.id).update(
            created_at=now - timedelta(days=1))

        # Cross-tenant payment (should NOT count)
        o_other = Order.objects.create(
            tenant=self.other_tenant, customer=self.customer2, status="READY"
        )
        Payment.objects.create(
            tenant=self.other_tenant,
            order=o_other,
            method=Payment.Method.CARD,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.IN,
            amount_cents=8888,
            reference="other",
        )

    def test_metrics_basic(self):
        r = self.client.get("/api/orders/metrics/")
        self.assertEqual(r.status_code, 200)
        data = r.json()

        self.assertIn("orders", data)
        self.assertIn("payments", data)

        # ready unpaid count should only reflect our tenant
        self.assertEqual(data["orders"]["ready_unpaid_count"], 1)

        # by_status should include at least these
        by_status = data["orders"]["by_status"]
        self.assertEqual(by_status.get("READY"), 2)
        self.assertEqual(by_status.get("IN_PROGRESS"), 1)
        self.assertEqual(by_status.get("CANCELLED"), 1)

        # payments today: in 2000, out 300, net 1700
        self.assertEqual(data["payments"]["in_cents_today"], 2000)
        self.assertEqual(data["payments"]["out_cents_today"], 300)
        self.assertEqual(data["payments"]["net_cents_today"], 1700)

    def test_metrics_ignores_voided_payments(self):
        Payment.objects.create(
            tenant=self.tenant,
            order=self.o_ready,
            method=Payment.Method.CARD,
            status=Payment.Status.VOIDED,
            direction=Payment.Direction.IN,
            amount_cents=7777,
            reference="voided",
        )

        r = self.client.get("/api/orders/metrics/")
        self.assertEqual(r.status_code, 200)
        data = r.json()

        self.assertEqual(data["payments"]["in_cents_today"], 2000)
        self.assertEqual(data["payments"]["out_cents_today"], 300)
        self.assertEqual(data["payments"]["net_cents_today"], 1700)


class TestOrderMetricsTimezoneWindow(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(name="T TZ", slug="t-tz")
        self.user = User.objects.create_user(username="admin", password="pass")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantMembership.Role.OWNER_ADMIN,
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT=self.tenant.slug)

        self.customer = Customer.objects.create(
            tenant=self.tenant, name="Patel", phone="7140000000"
        )

    def test_metrics_created_today_uses_tenant_timezone(self):
        now_utc = timezone.now()
        tz = ZoneInfo("UTC")
        now_local = now_utc.astimezone(tz)
        today_local = now_local.date()

        start_local = datetime(
            today_local.year, today_local.month, today_local.day, 0, 0, 0, tzinfo=tz
        )
        start = start_local.astimezone(timezone.UTC)

        in_order = Order.objects.create(
            tenant=self.tenant, customer=self.customer, status="RECEIVED"
        )
        out_order = Order.objects.create(
            tenant=self.tenant, customer=self.customer, status="RECEIVED"
        )

        Order.objects.filter(id=in_order.id).update(
            created_at=start + timedelta(minutes=5)
        )
        Order.objects.filter(id=out_order.id).update(
            created_at=start - timedelta(minutes=5)
        )

        r = self.client.get("/api/orders/metrics/")
        self.assertEqual(r.status_code, 200)
        data = r.json()

        self.assertEqual(data["orders"]["created_today"], 1)
