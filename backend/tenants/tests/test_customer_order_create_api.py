import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
from customers.models import Customer
from orders.models import Order

pytestmark = pytest.mark.operator_safety


def build_client(*, tenant, user, role) -> APIClient:
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=role,
        is_active=True,
    )
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


@pytest.mark.django_db
def test_create_order_for_customer():
    tenant = Tenant.objects.create(slug="t-cust-order", name="Cust Order")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    customer = Customer.objects.create(tenant=tenant, name="Alice")

    resp = client.post(f"/api/tenant/customers/{customer.id}/orders/", data={}, format="json")
    assert resp.status_code == 201
    data = resp.json()
    order = Order.objects.get(id=data["order_id"])
    assert order.customer_id == customer.id


@pytest.mark.django_db
def test_create_order_for_customer_cross_tenant_hidden():
    tenant_a = Tenant.objects.create(slug="t-cust-a", name="Cust A")
    tenant_b = Tenant.objects.create(slug="t-cust-b", name="Cust B")
    user = get_user_model().objects.create_user(username="admin2", password="pw")
    client = build_client(tenant=tenant_a, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    customer_b = Customer.objects.create(tenant=tenant_b, name="Other")

    resp = client.post(f"/api/tenant/customers/{customer_b.id}/orders/", data={}, format="json")
    assert resp.status_code == 404
