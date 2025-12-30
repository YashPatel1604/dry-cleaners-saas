from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant
from customers.models import Customer
from orders.models import Order

User = get_user_model()


class TestOrderSearch(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(name="T1", slug="t1")
        self.other_tenant = Tenant.objects.create(name="T2", slug="t2")

        self.user = User.objects.create_user(username="admin", password="pass")
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT=self.tenant.slug)

        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="Patel",
            phone="7140000000",
        )
        self.other_customer = Customer.objects.create(
            tenant=self.other_tenant,
            name="Other",
            phone="9999999999",
        )

        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            status="READY",
            settled_balance_due_cents=0,
        )

        Order.objects.create(
            tenant=self.other_tenant,
            customer=self.other_customer,
            status="READY",
            settled_balance_due_cents=0,
        )

    def test_search_requires_q(self):
        r = self.client.get("/api/orders/search/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("q", r.json())

    def test_search_by_customer_name(self):
        r = self.client.get("/api/orders/search/?q=pat")
        self.assertEqual(r.status_code, 200)

        ids = {o["id"] for o in r.json()}
        self.assertIn(self.order.id, ids)

    def test_search_is_tenant_scoped(self):
        r = self.client.get("/api/orders/search/?q=other")
        self.assertEqual(r.status_code, 200)

        ids = {o["id"] for o in r.json()}
        self.assertNotIn(self.order.id, ids)
