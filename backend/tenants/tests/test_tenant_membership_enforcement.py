import pytest
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety


@pytest.mark.django_db
def test_member_can_access_tenant_endpoint():
    tenant = Tenant.objects.create(slug="t-member", name="T Member")
    user = get_user_model().objects.create_user(username="u1", password="pw")
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)

    resp = client.get("/api/orders/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_non_member_cannot_access_tenant_endpoint():
    tenant = Tenant.objects.create(slug="t-nonmember", name="T Nonmember")
    user = get_user_model().objects.create_user(username="u2", password="pw")

    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)

    resp = client.get("/api/orders/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_inactive_membership_cannot_access_tenant_endpoint():
    tenant = Tenant.objects.create(slug="t-inactive", name="T Inactive")
    user = get_user_model().objects.create_user(username="u3", password="pw")
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OPERATOR,
        is_active=False,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)

    resp = client.get("/api/orders/")
    assert resp.status_code == 404
