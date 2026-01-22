import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety


def build_client(*, tenant, user, role, is_active=True) -> APIClient:
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=role,
        is_active=is_active,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


@pytest.mark.django_db
def test_membership_management_endpoints():
    User = get_user_model()
    tenant = Tenant.objects.create(slug="t-mgmt", name="T Mgmt")
    admin = User.objects.create_user(username="admin", password="pw")
    operator = User.objects.create_user(username="operator", password="pw")
    operator2 = User.objects.create_user(username="operator2", password="pw")
    outsider = User.objects.create_user(username="outsider", password="pw")
    new_user = User.objects.create_user(username="newuser", password="pw")

    admin_client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )
    operator_client = build_client(
        tenant=tenant, user=operator, role=TenantMembership.Role.OPERATOR
    )
    operator2_client = build_client(
        tenant=tenant, user=operator2, role=TenantMembership.Role.OPERATOR
    )

    resp = admin_client.get("/api/tenant/memberships/")
    assert resp.status_code == 200
    data = resp.json()
    assert {row["user"]["username"] for row in data} == {
        "admin",
        "operator",
        "operator2",
    }

    resp = operator_client.get("/api/tenant/memberships/")
    assert resp.status_code == 403

    outsider_client = APIClient()
    outsider_client.force_authenticate(user=outsider)
    outsider_client.credentials(HTTP_X_TENANT=tenant.slug)
    resp = outsider_client.get("/api/tenant/memberships/")
    assert resp.status_code == 404

    resp = admin_client.post(
        "/api/tenant/memberships/",
        data={"username": "newuser", "role": "OPERATOR"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["username"] == "newuser"

    inactive_user = User.objects.create_user(username="inactive", password="pw")
    inactive_membership = TenantMembership.objects.create(
        tenant=tenant,
        user=inactive_user,
        role=TenantMembership.Role.OPERATOR,
        is_active=False,
    )
    resp = admin_client.post(
        "/api/tenant/memberships/",
        data={"username": "inactive", "role": "OPERATOR"},
        format="json",
    )
    assert resp.status_code == 200
    inactive_membership.refresh_from_db()
    assert inactive_membership.is_active is True

    resp = admin_client.patch(
        f"/api/tenant/memberships/{admin.id}/",
        data={"is_active": False},
        format="json",
    )
    assert resp.status_code == 400

    resp = admin_client.patch(
        f"/api/tenant/memberships/{admin.id}/",
        data={"role": "OPERATOR"},
        format="json",
    )
    assert resp.status_code == 400

    resp = admin_client.patch(
        f"/api/tenant/memberships/{operator.id}/",
        data={"role": "OWNER_ADMIN"},
        format="json",
    )
    assert resp.status_code == 200

    resp = admin_client.patch(
        f"/api/tenant/memberships/{admin.id}/",
        data={"is_active": False},
        format="json",
    )
    assert resp.status_code == 200

    resp = operator2_client.post(
        "/api/tenant/memberships/",
        data={"username": "outsider", "role": "OPERATOR"},
        format="json",
    )
    assert resp.status_code == 403
    resp = operator2_client.patch(
        f"/api/tenant/memberships/{new_user.id}/",
        data={"role": "OPERATOR"},
        format="json",
    )
    assert resp.status_code == 403
