import pytest
from django.utils.dateparse import parse_datetime
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from customers.models import Customer
from orders.models import Order, OrderStatusEvent
from payments.models import Payment, Adjustment
from tenants.models import Tenant

pytestmark = pytest.mark.operator_safety


class TestTimelineDeterminism(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name="T1", slug="t1")
        self.user = get_user_model().objects.create_user(
            username="admin", password="pass"
        )
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT=self.tenant.slug)

        self.customer = Customer.objects.create(
            tenant=self.tenant, name="Patel", phone="7140000030"
        )
        self.order = Order.objects.create(
            tenant=self.tenant, customer=self.customer, status="RECEIVED"
        )

    def test_timeline_tie_breaker_order(self):
        fixed = timezone.now()

        Order.objects.filter(id=self.order.id).update(created_at=fixed)

        se = OrderStatusEvent.objects.create(
            tenant=self.tenant,
            order=self.order,
            from_status="RECEIVED",
            to_status="READY",
        )
        Payment.objects.create(
            tenant=self.tenant,
            order=self.order,
            method=Payment.Method.CASH,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.IN,
            amount_cents=1200,
            reference="p-1",
        )
        Adjustment.objects.create(
            tenant=self.tenant,
            order=self.order,
            kind=Adjustment.Kind.OTHER,
            status=Adjustment.Status.APPLIED,
            direction=Adjustment.Direction.OUT,
            amount_cents=100,
            reference="a-1",
        )

        OrderStatusEvent.objects.filter(id=se.id).update(created_at=fixed)
        Payment.objects.filter(order=self.order).update(created_at=fixed)
        Adjustment.objects.filter(order=self.order).update(created_at=fixed)

        Order.objects.filter(id=self.order.id).update(
            settled_at=fixed,
            settled_total_cents=1000,
            settled_paid_cents=1200,
            settled_change_cents=200,
            settled_balance_due_cents=0,
        )

        r = self.client.get(f"/api/orders/{self.order.id}/timeline/")
        self.assertEqual(r.status_code, 200)
        events = r.json()

        def same_instant(ts: str) -> bool:
            parsed = parse_datetime(ts)
            if parsed is None:
                return False
            return parsed.timestamp() == fixed.timestamp()

        kinds = [e["kind"] for e in events if same_instant(e["at"])]
        expected = [
            "order.created",
            "status.change",
            "payment.created",
            "adjustment.applied",
            "settlement.snapshot",
        ]
        self.assertEqual(kinds, expected)
