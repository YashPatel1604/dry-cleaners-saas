import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
from customers.models import Customer

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
def test_customers_search_by_name_email_phone_and_last4():
    tenant = Tenant.objects.create(slug="t-cust-search", name="Cust Search")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    cust_a = Customer.objects.create(
        tenant=tenant,
        name="Alicia Keys",
        phone="714-555-1212",
        email="alicia@example.com",
    )
    cust_b = Customer.objects.create(
        tenant=tenant,
        name="Bob Smith",
        phone="949 222 3333",
        email="bob@other.com",
    )

    r = client.get("/api/tenant/customers/search/?q=alicia")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert cust_a.id in ids

    r = client.get("/api/tenant/customers/search/?q=other.com")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert cust_b.id in ids

    r = client.get("/api/tenant/customers/search/?q=555")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert cust_a.id in ids

    r = client.get("/api/tenant/customers/search/?q=1212")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert cust_a.id in ids


@pytest.mark.django_db
def test_customers_search_q_too_short_returns_empty():
    tenant = Tenant.objects.create(slug="t-cust-short", name="Cust Short")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    Customer.objects.create(tenant=tenant, name="Alpha")

    r = client.get("/api/tenant/customers/search/?q=a")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.django_db
def test_customers_search_limit_cap():
    tenant = Tenant.objects.create(slug="t-cust-limit", name="Cust Limit")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    for i in range(60):
        Customer.objects.create(tenant=tenant, name=f"Test Customer {i}")

    r = client.get("/api/tenant/customers/search/?q=Test&limit=200")
    assert r.status_code == 200
    assert len(r.json()) == 50
