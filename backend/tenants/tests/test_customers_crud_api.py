import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership

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
def test_customers_crud_owner_admin():
    tenant = Tenant.objects.create(slug="t-cust-admin", name="Cust Admin")
    admin = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN)

    resp = client.post(
        "/api/tenant/customers/",
        data={"name": "Alice", "phone": "714-555-1212", "email": "A@EXAMPLE.COM"},
        format="json",
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]

    resp = client.get("/api/tenant/customers/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get(f"/api/tenant/customers/{cid}/")
    assert resp.status_code == 200
    assert resp.json()["email"] == "a@example.com"

    resp = client.patch(
        f"/api/tenant/customers/{cid}/",
        data={"notes": "VIP"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "VIP"

    resp = client.delete(f"/api/tenant/customers/{cid}/")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_customers_crud_operator_allowed():
    tenant = Tenant.objects.create(slug="t-cust-op", name="Cust Op")
    operator = get_user_model().objects.create_user(username="operator", password="pw")
    client = build_client(tenant=tenant, user=operator, role=TenantMembership.Role.OPERATOR)

    resp = client.post(
        "/api/tenant/customers/",
        data={"name": "Bob"},
        format="json",
    )
    assert resp.status_code == 201


@pytest.mark.django_db
def test_customers_crud_non_member_404():
    tenant = Tenant.objects.create(slug="t-cust-out", name="Cust Out")
    outsider = get_user_model().objects.create_user(username="outsider", password="pw")

    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=outsider)
    client.credentials(HTTP_X_TENANT=tenant.slug)

    resp = client.get("/api/tenant/customers/")
    assert resp.status_code == 404
    resp = client.post(
        "/api/tenant/customers/",
        data={"name": "X"},
        format="json",
    )
    assert resp.status_code == 404
