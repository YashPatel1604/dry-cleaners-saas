from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from tenants.models import Tenant
from tenants.models import TenantMembership
from orders.models import Order

from customers.models import Customer

User = get_user_model()


class TestOrderTimeline(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="T1", slug="t1", is_active=True)
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            is_staff=True,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantMembership.Role.OWNER_ADMIN,
            is_active=True,
        )

        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="Test Customer",
            phone="5550001111",
        )

        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            status="CREATED",
        )

        self.client.force_authenticate(user=self.user)
        self.tenant_headers = {"HTTP_X_TENANT": self.tenant.slug}

    def test_timeline_includes_payment_events(self):
        # IMPORTANT: timeline is based on AuditEvents,
        # so we must create the payment through the API (which emits events).
        create_resp = self.client.post(
            "/api/payments/",
            {
                "order": self.order.id,
                "amount_cents": 500,
                "method": "CASH",
                "reference": "t-1",
            },
            format="json",
            **self.tenant_headers,
        )
        self.assertIn(create_resp.status_code, (200, 201), create_resp.content)

        # now timeline should include payment.created (or payment.replayed if 200)
        timeline_resp = self.client.get(
            f"/api/orders/{self.order.id}/audit/",
            **self.tenant_headers,
        )
        self.assertEqual(timeline_resp.status_code, 200)

        data = timeline_resp.json()
        self.assertEqual(data["order_id"], self.order.id)
        self.assertIn("events", data)

        # Must have at least 1 event now
        self.assertGreaterEqual(len(data["events"]), 1)

        actions = [e["action"] for e in data["events"]]
        self.assertTrue(
            ("payment.created" in actions) or ("payment.replayed" in actions),
            actions,
        )

        # If your timeline includes after.order_id, enforce it matches
        for e in data["events"]:
            after = e.get("after") or {}
            if "order_id" in after:
                self.assertEqual(after["order_id"], self.order.id)

    def test_timeline_tenant_isolation(self):
        other = Tenant.objects.create(name="T2", slug="t2", is_active=True)
        other_customer = Customer.objects.create(
            tenant=other,
            name="Other Customer",
            phone="5550002222",
        )
        other_order = Order.objects.create(
            tenant=other,
            customer=other_customer,
            status="CREATED",
        )

        resp = self.client.get(
            f"/api/orders/{other_order.id}/audit/",
            **self.tenant_headers,
        )

        # depending on tenant filtering style, could be 404 or 403
        self.assertIn(resp.status_code, (403, 404))
