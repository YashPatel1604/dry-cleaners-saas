import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
from tenants.models import Tenant

pytestmark = pytest.mark.operator_safety


def build_client(*, tenant, user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


@pytest.mark.django_db
def test_operator_endpoints_tenant_isolation(django_user_model):
    tenant_a = Tenant.objects.create(slug="t-a", name="Tenant A")
    tenant_b = Tenant.objects.create(slug="t-b", name="Tenant B")

    user = django_user_model.objects.create_user(username="u1", password="pw")
    client_b = build_client(tenant=tenant_b, user=user)

    customer_a = Customer.objects.create(
        tenant=tenant_a,
        name="Patel",
        phone="7140000050",
    )

    order_a = Order.objects.create(
        tenant=tenant_a,
        customer=customer_a,
        status="COMPLETED",
        due_at=timezone.now(),
    )

    endpoints = [
        ("GET", f"/api/orders/{order_a.id}/"),
        ("GET", f"/api/orders/{order_a.id}/timeline/"),
        ("GET", f"/api/orders/{order_a.id}/receipt/"),
        ("GET", f"/api/orders/{order_a.id}/receipt/print/"),
        ("POST", f"/api/orders/{order_a.id}/pickup/"),
        ("POST", f"/api/orders/{order_a.id}/settle/"),
    ]

    for method, path in endpoints:
        if method == "GET":
            resp = client_b.get(path)
        else:
            resp = client_b.post(path, data={}, format="json")
        assert resp.status_code != 200
        assert resp.status_code in (400, 403, 404)
