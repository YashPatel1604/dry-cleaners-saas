from django.test import TestCase
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant
from customers.models import Customer
from orders.models import Order

User = get_user_model()

pytestmark = pytest.mark.operator_safety


class TestOrderQueue(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(name="T1", slug="t1")
        self.other_tenant = Tenant.objects.create(name="T2", slug="t2")

        self.user = User.objects.create_user(username="admin", password="pass")
        self.client.force_authenticate(user=self.user)

        # IMPORTANT: set tenant header for middleware
        self.client.credentials(HTTP_X_TENANT=self.tenant.slug)

        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="Patel",
            phone="7140000000",
        )
        self.customer2 = Customer.objects.create(
            tenant=self.other_tenant,
            name="Other",
            phone="9490000000",
        )

        # In-tenant orders
        self.o_ready_paid = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            status="READY",
            settled_balance_due_cents=0,
        )
        self.o_ready_unpaid = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            status="READY",
            settled_balance_due_cents=500,
        )
        self.o_in_progress = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            status="IN_PROGRESS",
            settled_balance_due_cents=0,
        )

        # Cross-tenant order (must never show up)
        self.o_other_ready = Order.objects.create(
            tenant=self.other_tenant,
            customer=self.customer2,
            status="READY",
            settled_balance_due_cents=999,
        )

    def _results(self, response_json):
        """
        Queue endpoint may return either:
        - a plain list (no pagination), or
        - a paginated dict {"count":..., "next":..., "previous":..., "results":[...]}
        """
        return response_json["results"] if isinstance(response_json, dict) else response_json

    def test_queue_requires_status(self):
        r = self.client.get("/api/orders/queue/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("status", r.json())

    def test_queue_filters_by_status(self):
        r = self.client.get("/api/orders/queue/?status=READY")
        self.assertEqual(r.status_code, 200)

        data = r.json()
        results = self._results(data)
        ids = {o["id"] for o in results}

        self.assertIn(self.o_ready_paid.id, ids)
        self.assertIn(self.o_ready_unpaid.id, ids)
        self.assertNotIn(self.o_in_progress.id, ids)

        # tenant isolation
        self.assertNotIn(self.o_other_ready.id, ids)

    def test_queue_ready_unpaid(self):
        r = self.client.get("/api/orders/queue/?status=READY&ready_unpaid=1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get("X-Ready-Unpaid-Mode"), "settled_only")

        data = r.json()
        if isinstance(data, dict):
            self.assertEqual(data.get("ready_unpaid_mode"), "settled_only")
        results = self._results(data)
        ids = {o["id"] for o in results}

        self.assertIn(self.o_ready_unpaid.id, ids)
        self.assertNotIn(self.o_ready_paid.id, ids)
