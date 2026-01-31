import pytest
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership, TenantInvite, TenantInviteEvent

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
@override_settings(RETURN_INVITE_TOKEN=True)
def test_invites_admin_api():
    User = get_user_model()
    tenant = Tenant.objects.create(slug="t-invite", name="T Invite")
    admin = User.objects.create_user(username="admin", password="pw")
    operator = User.objects.create_user(username="operator", password="pw")
    outsider = User.objects.create_user(username="outsider", password="pw")

    admin_client = build_client(
        tenant=tenant, user=admin, role=TenantMembership.Role.OWNER_ADMIN
    )
    operator_client = build_client(
        tenant=tenant, user=operator, role=TenantMembership.Role.OPERATOR
    )

    outsider_client = APIClient()
    outsider_client.force_authenticate(user=outsider)
    outsider_client.credentials(HTTP_X_TENANT=tenant.slug)
    resp = outsider_client.get("/api/tenant/invites/")
    assert resp.status_code == 404
    resp = outsider_client.post("/api/tenant/invites/", data={"email": "a@b.com"}, format="json")
    assert resp.status_code == 404

    resp = operator_client.get("/api/tenant/invites/")
    assert resp.status_code == 403
    resp = operator_client.post("/api/tenant/invites/", data={"email": "a@b.com"}, format="json")
    assert resp.status_code == 403

    resp = admin_client.post(
        "/api/tenant/invites/",
        data={"email": "Operator@Email.com"},
        format="json",
    )
    assert resp.status_code == 201
    token1 = resp.json()["token"]
    invite = TenantInvite.objects.get(tenant=tenant, email="operator@email.com")
    assert invite.role == TenantInvite.Role.OPERATOR

    resp = admin_client.post(
        "/api/tenant/invites/",
        data={"email": "operator@email.com"},
        format="json",
    )
    assert resp.status_code == 201
    token2 = resp.json()["token"]
    assert token1 != token2

    events = TenantInviteEvent.objects.filter(tenant=tenant, email="operator@email.com")
    assert events.filter(event_type=TenantInviteEvent.EventType.CREATED).count() == 1
    assert events.filter(event_type=TenantInviteEvent.EventType.RESENT).count() == 1

    resp = admin_client.get("/api/tenant/invites/")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["email"] == "operator@email.com"
    assert "token" not in data[0]
    assert "token_hash" not in data[0]

    resp = admin_client.post(f"/api/tenant/invites/{invite.id}/revoke/")
    assert resp.status_code == 200
    invite.refresh_from_db()
    assert invite.revoked_at is not None
    assert TenantInviteEvent.objects.filter(
        tenant=tenant,
        email="operator@email.com",
        event_type=TenantInviteEvent.EventType.REVOKED,
    ).exists()

    accepted_invite = TenantInvite.objects.create(
        tenant=tenant,
        email="accepted@email.com",
        role=TenantInvite.Role.OPERATOR,
        token_hash="x",
        expires_at=timezone.now(),
        accepted_at=timezone.now(),
        created_by=admin,
    )
    resp = admin_client.post(f"/api/tenant/invites/{accepted_invite.id}/revoke/")
    assert resp.status_code == 400
