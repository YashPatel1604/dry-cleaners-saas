import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership, TenantConfigEvent

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
def test_owner_admin_can_deactivate_tenant():
    tenant = Tenant.objects.create(slug="t-deact", name="Deactivate")
    admin = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    resp = client.post("/api/tenant/deactivate/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "deactivated"}

    tenant.refresh_from_db()
    assert tenant.is_active is False
    assert tenant.deactivated_at is not None
    assert TenantConfigEvent.objects.filter(
        tenant=tenant,
        key="tenant_status",
        new_value="deactivated",
    ).exists()


@pytest.mark.django_db
def test_deactivated_tenant_blocks_scoped_endpoints():
    tenant = Tenant.objects.create(slug="t-deact-block", name="Deactivate Block")
    admin = get_user_model().objects.create_user(username="admin2", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    resp = client.post("/api/tenant/deactivate/")
    assert resp.status_code == 200

    assert client.get("/api/tenant/settings/").status_code == 404
    assert client.get("/api/tenant/memberships/").status_code == 404
    assert client.get("/api/orders/").status_code == 404


@pytest.mark.django_db
def test_me_tenants_excludes_deactivated_tenant():
    tenant = Tenant.objects.create(slug="t-deact-me", name="Deactivate Me")
    user = get_user_model().objects.create_user(username="user", password="pw")
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    )

    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    assert client.post("/api/tenant/deactivate/").status_code == 200

    resp = client.get("/api/me/tenants/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_non_member_cannot_deactivate():
    tenant = Tenant.objects.create(slug="t-deact-404", name="Deactivate 404")
    outsider = get_user_model().objects.create_user(username="outsider", password="pw")
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=outsider)
    client.credentials(HTTP_X_TENANT=tenant.slug)

    resp = client.post("/api/tenant/deactivate/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_deactivate_already_deactivated_returns_404():
    tenant = Tenant.objects.create(slug="t-deact-again", name="Deactivate Again")
    admin = get_user_model().objects.create_user(username="admin3", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    assert client.post("/api/tenant/deactivate/").status_code == 200
    resp = client.post("/api/tenant/deactivate/")
    assert resp.status_code == 404
