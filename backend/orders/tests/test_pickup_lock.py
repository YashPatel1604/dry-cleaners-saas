from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework.test import APIClient

from tenants.models import Tenant
from customers.models import Customer
from orders.models import Order

User = get_user_model()


class TestPickupSettlementLock(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.tenant = Tenant.objects.create(name="T1", slug="t1")
        self.user = User.objects.create_user(username="admin", password="pass")

        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT=self.tenant.slug)

        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="Patel",
            phone="7140000000",
        )

        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            status="READY",
            due_at=timezone.now(),
            settled_at=timezone.now(),  # 🔒 already settled
        )

    def test_pickup_blocked_when_settled(self):
        r = self.client.post(
            f"/api/orders/{self.order.id}/pickup/", data={}, format="json")
        self.assertEqual(r.status_code, 400)

        body = r.json()
        self.assertIn("order", body)
