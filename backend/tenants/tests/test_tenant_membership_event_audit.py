import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership, TenantMembershipEvent

pytestmark = pytest.mark.operator_safety


def build_client(*, tenant, user, role) -> APIClient:
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=role,
        is_active=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


@pytest.mark.django_db
def test_membership_event_audit_rows():
    User = get_user_model()
    tenant = Tenant.objects.create(slug="t-audit", name="T Audit")
    admin = User.objects.create_user(username="admin", password="pw")
    target = User.objects.create_user(username="target", password="pw")

    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    resp = client.post(
        "/api/tenant/memberships/",
        data={"username": "target", "role": "OPERATOR"},
        format="json",
    )
    assert resp.status_code == 201

    created_event = TenantMembershipEvent.objects.filter(
        tenant=tenant, subject_user=target
    ).order_by("created_at").first()
    assert created_event.action == TenantMembershipEvent.Action.CREATED
    assert created_event.new_role == "OPERATOR"
    assert created_event.is_active_after is True
    assert created_event.actor_id == admin.id

    resp = client.patch(
        f"/api/tenant/memberships/{target.id}/",
        data={"role": "OWNER_ADMIN", "is_active": False},
        format="json",
    )
    assert resp.status_code == 200

    events = list(
        TenantMembershipEvent.objects.filter(tenant=tenant, subject_user=target)
        .order_by("created_at", "id")
    )
    assert events[-2].action == TenantMembershipEvent.Action.ROLE_CHANGED
    assert events[-2].old_role == "OPERATOR"
    assert events[-2].new_role == "OWNER_ADMIN"
    assert events[-1].action == TenantMembershipEvent.Action.DEACTIVATED
    assert events[-1].is_active_before is True
    assert events[-1].is_active_after is False


@pytest.mark.django_db
def test_membership_tenant_scoping():
    User = get_user_model()
    tenant_a = Tenant.objects.create(slug="t-audit-a", name="T Audit A")
    tenant_b = Tenant.objects.create(slug="t-audit-b", name="T Audit B")
    admin_a = User.objects.create_user(username="admin-a", password="pw")
    admin_b = User.objects.create_user(username="admin-b", password="pw")
    user_b = User.objects.create_user(username="user-b", password="pw")

    client_a = build_client(
        tenant=tenant_a, user=admin_a, role=TenantMembership.Role.OWNER_ADMIN
    )
    build_client(
        tenant=tenant_b, user=admin_b, role=TenantMembership.Role.OWNER_ADMIN
    )
    TenantMembership.objects.create(
        tenant=tenant_b,
        user=user_b,
        role=TenantMembership.Role.OPERATOR,
        is_active=True,
    )

    resp = client_a.patch(
        f"/api/tenant/memberships/{user_b.id}/",
        data={"role": "OWNER_ADMIN"},
        format="json",
    )
    assert resp.status_code == 404
