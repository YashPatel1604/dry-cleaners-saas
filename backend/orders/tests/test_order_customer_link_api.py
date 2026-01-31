import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
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
def test_order_customer_link_within_tenant():
    tenant = Tenant.objects.create(slug="t-order-cust", name="Order Cust")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    customer = Customer.objects.create(tenant=tenant, name="Alice")
    order = Order.objects.create(tenant=tenant)

    resp = client.patch(
        f"/api/orders/{order.id}/customer/",
        data={"customer_id": customer.id},
        format="json",
    )
    assert resp.status_code == 200

    order.refresh_from_db()
    assert order.customer_id == customer.id


@pytest.mark.django_db
def test_order_customer_link_cross_tenant_hidden():
    tenant_a = Tenant.objects.create(slug="t-order-a", name="Order A")
    tenant_b = Tenant.objects.create(slug="t-order-b", name="Order B")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant_a, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    order = Order.objects.create(tenant=tenant_a)
    other_customer = Customer.objects.create(tenant=tenant_b, name="Other")

    resp = client.patch(
        f"/api/orders/{order.id}/customer/",
        data={"customer_id": other_customer.id},
        format="json",
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_order_customer_clear_allowed():
    tenant = Tenant.objects.create(slug="t-order-clear", name="Order Clear")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    customer = Customer.objects.create(tenant=tenant, name="Alice")
    order = Order.objects.create(tenant=tenant, customer=customer)

    resp = client.patch(
        f"/api/orders/{order.id}/customer/",
        data={"customer_id": None},
        format="json",
    )
    assert resp.status_code == 200

    order.refresh_from_db()
    assert order.customer_id is None


@pytest.mark.django_db
def test_order_customer_link_settled_does_not_change_snapshots():
    tenant = Tenant.objects.create(slug="t-order-settled", name="Order Settled")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    customer = Customer.objects.create(tenant=tenant, name="Alice")
    order = Order.objects.create(
        tenant=tenant,
        settled_at=timezone.now(),
        settled_total_cents=1000,
        settled_paid_cents=1000,
        settled_change_cents=0,
        settled_balance_due_cents=0,
    )

    resp = client.patch(
        f"/api/orders/{order.id}/customer/",
        data={"customer_id": customer.id},
        format="json",
    )
    assert resp.status_code == 200

    order.refresh_from_db()
    assert order.customer_id == customer.id
    assert order.settled_total_cents == 1000
    assert order.settled_paid_cents == 1000
    assert order.settled_change_cents == 0
    assert order.settled_balance_due_cents == 0
