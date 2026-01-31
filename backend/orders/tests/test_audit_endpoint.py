import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from customers.models import Customer
from orders.models import Order
from payments.models import Payment, Adjustment
from tenants.models import Tenant, TenantMembership

User = get_user_model()

pytestmark = pytest.mark.operator_safety


class TestOrderAuditEndpoint(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(name="T1", slug="t1")
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
        self.order = Order.objects.create(
            tenant=self.tenant, customer=self.customer, status="RECEIVED"
        )

        self.payment = Payment.objects.create(
            tenant=self.tenant,
            order=self.order,
            method=Payment.Method.CARD,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.IN,
            amount_cents=500,
            reference="p-audit",
        )

        self.adjustment = Adjustment.objects.create(
            tenant=self.tenant,
            order=self.order,
            kind=Adjustment.Kind.OTHER,
            status=Adjustment.Status.APPLIED,
            direction=Adjustment.Direction.OUT,
            amount_cents=100,
            reference="a-audit",
            note="discount",
        )

    def test_audit_endpoint_returns_order_payment_adjustment(self):
        now = timezone.now()
        AuditEvent.objects.create(
            tenant=self.tenant,
            request_id="req-1",
            actor_type=AuditEvent.ActorType.USER,
            actor_id=str(self.user.id),
            actor_label="admin",
            action="order.created",
            entity_type="order",
            entity_id=str(self.order.id),
            before=None,
            after={"status": "RECEIVED"},
            metadata={},
            created_at=now,
        )
        AuditEvent.objects.create(
            tenant=self.tenant,
            request_id="req-2",
            actor_type=AuditEvent.ActorType.USER,
            actor_id=str(self.user.id),
            actor_label="admin",
            action="payment.created",
            entity_type="payment",
            entity_id=str(self.payment.id),
            before=None,
            after={"amount_cents": 500},
            metadata={},
            created_at=now,
        )
        AuditEvent.objects.create(
            tenant=self.tenant,
            request_id="req-3",
            actor_type=AuditEvent.ActorType.USER,
            actor_id=str(self.user.id),
            actor_label="admin",
            action="adjustment.applied",
            entity_type="adjustment",
            entity_id=str(self.adjustment.id),
            before=None,
            after={"amount_cents": 100},
            metadata={},
            created_at=now,
        )

        r = self.client.get(f"/api/orders/{self.order.id}/audit/")
        self.assertEqual(r.status_code, 200)
        data = r.json()

        self.assertEqual(data["order_id"], self.order.id)
        self.assertEqual(data["count"], 3)

        entity_types = {e["entity_type"] for e in data["events"]}
        self.assertEqual(entity_types, {"order", "payment", "adjustment"})
