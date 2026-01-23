import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import (
    Tenant,
    TenantMembership,
    TenantMembershipEvent,
    TenantConfigEvent,
    TenantInviteEvent,
)

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
def test_audit_endpoints_owner_admin_scoped():
    User = get_user_model()
    tenant_a = Tenant.objects.create(slug="t-audit-a", name="Audit A")
    tenant_b = Tenant.objects.create(slug="t-audit-b", name="Audit B")
    admin = User.objects.create_user(username="admin", password="pw")
    subject = User.objects.create_user(username="subject", password="pw")

    admin_client = build_client(
        tenant=tenant_a, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    TenantMembershipEvent.objects.create(
        tenant=tenant_a,
        actor=admin,
        subject_user=subject,
        action=TenantMembershipEvent.Action.CREATED,
    )
    TenantMembershipEvent.objects.create(
        tenant=tenant_b,
        actor=admin,
        subject_user=subject,
        action=TenantMembershipEvent.Action.CREATED,
    )

    TenantConfigEvent.objects.create(
        tenant=tenant_a,
        actor=admin,
        key="tax_rate_bps",
        old_value="800",
        new_value="900",
    )
    TenantConfigEvent.objects.create(
        tenant=tenant_b,
        actor=admin,
        key="tax_rate_bps",
        old_value="800",
        new_value="900",
    )

    TenantInviteEvent.objects.create(
        tenant=tenant_a,
        actor=admin,
        email="invitee@example.com",
        event_type=TenantInviteEvent.EventType.CREATED,
        metadata={"email_sent": True},
    )
    TenantInviteEvent.objects.create(
        tenant=tenant_b,
        actor=admin,
        email="invitee@example.com",
        event_type=TenantInviteEvent.EventType.CREATED,
        metadata={"email_sent": True},
    )

    resp = admin_client.get("/api/tenant/audit/memberships/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["subject_user_id"] == subject.id

    resp = admin_client.get("/api/tenant/audit/config/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["key"] == "tax_rate_bps"

    resp = admin_client.get("/api/tenant/audit/invites/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["email"] == "invitee@example.com"


@pytest.mark.django_db
def test_audit_endpoints_non_member_gets_404():
    tenant = Tenant.objects.create(slug="t-audit-404", name="Audit 404")
    outsider = get_user_model().objects.create_user(username="outsider", password="pw")
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=outsider)
    client.credentials(HTTP_X_TENANT=tenant.slug)

    resp = client.get("/api/tenant/audit/memberships/")
    assert resp.status_code == 404

    resp = client.get("/api/tenant/audit/config/")
    assert resp.status_code == 404

    resp = client.get("/api/tenant/audit/invites/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_audit_endpoints_operator_forbidden():
    tenant = Tenant.objects.create(slug="t-audit-403", name="Audit 403")
    operator = get_user_model().objects.create_user(username="operator", password="pw")
    client = build_client(
        tenant=tenant, user=operator, role=TenantMembership.Role.OPERATOR
    )

    resp = client.get("/api/tenant/audit/memberships/")
    assert resp.status_code in (403, 404)

    resp = client.get("/api/tenant/audit/config/")
    assert resp.status_code in (403, 404)

    resp = client.get("/api/tenant/audit/invites/")
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_audit_pagination_limit_cap():
    tenant = Tenant.objects.create(slug="t-audit-limit", name="Audit Limit")
    admin = get_user_model().objects.create_user(username="admin2", password="pw")
    client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )

    for i in range(0, 250):
        TenantInviteEvent.objects.create(
            tenant=tenant,
            actor=admin,
            email=f"invitee{i}@example.com",
            event_type=TenantInviteEvent.EventType.CREATED,
            metadata={"email_sent": True},
        )

    resp = client.get("/api/tenant/audit/invites/?limit=500")
    assert resp.status_code == 200
    assert len(resp.json()) == 200
