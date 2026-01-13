from django.test import TestCase
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant
from customers.models import Customer
from orders.models import Order, OrderStatusEvent
from payments.models import Payment, Adjustment

User = get_user_model()

pytestmark = pytest.mark.operator_safety


class TestOrderTimeline(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(name="T1", slug="t1")
        self.other_tenant = Tenant.objects.create(name="T2", slug="t2")

        self.user = User.objects.create_user(username="admin", password="pass")
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT=self.tenant.slug)

        self.customer = Customer.objects.create(
            tenant=self.tenant, name="Patel", phone="7140000000")
        self.customer2 = Customer.objects.create(
            tenant=self.other_tenant, name="Other", phone="9490000000")

        self.order = Order.objects.create(
            tenant=self.tenant, customer=self.customer, status="RECEIVED")
        self.other_order = Order.objects.create(
            tenant=self.other_tenant, customer=self.customer2, status="RECEIVED")

    def test_timeline_tenant_scoped(self):
        r = self.client.get(f"/api/orders/{self.other_order.id}/timeline/")
        self.assertIn(r.status_code, (404, 403))

    def test_timeline_includes_expected_kinds(self):
        OrderStatusEvent.objects.create(
            tenant=self.tenant,
            order=self.order,
            from_status="RECEIVED",
            to_status="READY",
            changed_by=self.user,
            note="ready",
        )

        Payment.objects.create(
            tenant=self.tenant,
            order=self.order,
            method=Payment.Method.CASH,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.IN,
            amount_cents=2000,
            reference="",
            note="",
        )

        Adjustment.objects.create(
            tenant=self.tenant,
            order=self.order,
            kind=Adjustment.Kind.OTHER,
            status=Adjustment.Status.APPLIED,
            direction=Adjustment.Direction.OUT,
            amount_cents=500,
            reference=None,
            note="discount",
        )

        self.order.settled_at = timezone.now()
        self.order.settled_total_cents = 2500
        self.order.settled_paid_cents = 2000
        self.order.settled_change_cents = 0
        self.order.settled_balance_due_cents = 500
        self.order.save()

        r = self.client.get(f"/api/orders/{self.order.id}/timeline/")
        self.assertEqual(r.status_code, 200)

        events = r.json()
        kinds = [e["kind"] for e in events]

        self.assertIn("order.created", kinds)
        self.assertIn("status.change", kinds)
        self.assertIn("payment.created", kinds)
        self.assertIn("adjustment.applied", kinds)
        self.assertIn("settlement.snapshot", kinds)

    def test_timeline_sorted(self):
        OrderStatusEvent.objects.create(
            tenant=self.tenant,
            order=self.order,
            from_status="RECEIVED",
            to_status="IN_PROGRESS",
            changed_by=self.user,
        )

        r = self.client.get(f"/api/orders/{self.order.id}/timeline/")
        self.assertEqual(r.status_code, 200)

        events = r.json()
        ats = [e["at"] for e in events]
        self.assertEqual(ats, sorted(ats))

    def test_timeline_event_schema(self):
        OrderStatusEvent.objects.create(
            tenant=self.tenant,
            order=self.order,
            from_status="RECEIVED",
            to_status="READY",
            changed_by=self.user,
        )

        Payment.objects.create(
            tenant=self.tenant,
            order=self.order,
            method=Payment.Method.CARD,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.IN,
            amount_cents=1200,
            reference="p-schema",
        )

        r = self.client.get(f"/api/orders/{self.order.id}/timeline/")
        self.assertEqual(r.status_code, 200)

        events = r.json()
        required_keys = {
            "id",
            "at",
            "kind",
            "title",
            "summary",
            "actor",
            "amount",
            "refs",
            "meta",
        }

        for e in events:
            self.assertEqual(set(e.keys()), required_keys)
            self.assertIn("type", e["actor"])
            self.assertIn("id", e["actor"])
            self.assertIn("label", e["actor"])
            self.assertIn("order_id", e["refs"])
