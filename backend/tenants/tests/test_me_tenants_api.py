import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety


@pytest.mark.django_db
def test_me_tenants_single_membership():
    user = get_user_model().objects.create_user(
        username="u1", email="u1@example.com", password="pass"
    )
    tenant = Tenant.objects.create(slug="t-one", name="Alpha")
    TenantMembership.objects.create(
        tenant=tenant, user=user, role=TenantMembership.Role.OPERATOR, is_active=True
    )

    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    resp = client.get("/api/me/tenants/")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "tenant_id": tenant.id,
            "tenant_slug": "t-one",
            "tenant_name": "Alpha",
            "role": TenantMembership.Role.OPERATOR,
        }
    ]


@pytest.mark.django_db
def test_me_tenants_multiple_memberships():
    user = get_user_model().objects.create_user(
        username="u2", email="u2@example.com", password="pass"
    )
    tenant_a = Tenant.objects.create(slug="t-a", name="Alpha")
    tenant_b = Tenant.objects.create(slug="t-b", name="Beta")
    TenantMembership.objects.create(
        tenant=tenant_b, user=user, role=TenantMembership.Role.OPERATOR, is_active=True
    )
    TenantMembership.objects.create(
        tenant=tenant_a, user=user, role=TenantMembership.Role.OWNER_ADMIN, is_active=True
    )

    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    resp = client.get("/api/me/tenants/")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "tenant_id": tenant_a.id,
            "tenant_slug": "t-a",
            "tenant_name": "Alpha",
            "role": TenantMembership.Role.OWNER_ADMIN,
        },
        {
            "tenant_id": tenant_b.id,
            "tenant_slug": "t-b",
            "tenant_name": "Beta",
            "role": TenantMembership.Role.OPERATOR,
        },
    ]


@pytest.mark.django_db
def test_me_tenants_excludes_inactive_membership():
    user = get_user_model().objects.create_user(
        username="u3", email="u3@example.com", password="pass"
    )
    tenant = Tenant.objects.create(slug="t-inactive", name="Inactive")
    TenantMembership.objects.create(
        tenant=tenant, user=user, role=TenantMembership.Role.OPERATOR, is_active=False
    )

    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    resp = client.get("/api/me/tenants/")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_me_tenants_requires_auth():
    client = APIClient(raise_request_exception=False)
    resp = client.get("/api/me/tenants/")

    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_me_tenants_no_x_tenant_required():
    user = get_user_model().objects.create_user(
        username="u4", email="u4@example.com", password="pass"
    )
    tenant = Tenant.objects.create(slug="t-nt", name="No Tenant")
    TenantMembership.objects.create(
        tenant=tenant, user=user, role=TenantMembership.Role.OPERATOR, is_active=True
    )

    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    resp = client.get("/api/me/tenants/")

    assert resp.status_code == 200
    assert len(resp.json()) == 1
