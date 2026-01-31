import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
from payments.models import Payment, Adjustment
from tenants.models import Tenant, TenantMembership

User = get_user_model()

pytestmark = pytest.mark.operator_safety


def create_order_with_financials(*, tenant, customer, ref_prefix: str) -> Order:
    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="READY",
        subtotal_cents=0,
        tax_cents=0,
        total_cents=0,
        paid_cents=0,
    )

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1000,
        reference=f"{ref_prefix}-pay",
    )

    Adjustment.objects.create(
        tenant=tenant,
        order=order,
        kind=Adjustment.Kind.OTHER,
        status=Adjustment.Status.APPLIED,
        direction=Adjustment.Direction.OUT,
        amount_cents=100,
        reference=f"{ref_prefix}-adj",
    )

    return order


class TestOrderListQueryEfficiency(TestCase):
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

    def _count_list_queries(self) -> int:
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get("/api/orders/")
            self.assertEqual(resp.status_code, 200)
        return len(ctx)

    def test_order_list_query_count_scales(self):
        create_order_with_financials(
            tenant=self.tenant, customer=self.customer, ref_prefix="o1"
        )

        count_one = self._count_list_queries()

        for i in range(2, 7):
            create_order_with_financials(
                tenant=self.tenant,
                customer=self.customer,
                ref_prefix=f"o{i}",
            )

        count_many = self._count_list_queries()

        self.assertLessEqual(count_many, count_one + 2)
