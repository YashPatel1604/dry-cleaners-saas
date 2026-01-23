import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantInvite, TenantInviteEvent, TenantMembership

pytestmark = pytest.mark.operator_safety


def build_admin_client(*, tenant, user) -> APIClient:
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    )
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


@override_settings(DEBUG=True)
@pytest.mark.django_db
def test_invite_returns_token_when_debug(monkeypatch):
    tenant = Tenant.objects.create(slug="t-invite", name="T Invite")
    admin = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_admin_client(tenant=tenant, user=admin)

    calls = []

    def fake_send(*, tenant, email, token, invited_by_user):
        calls.append((tenant, email, token, invited_by_user))

    monkeypatch.setattr("tenants.views.send_tenant_invite_email", fake_send)

    resp = client.post(
        "/api/tenant/invites/",
        data={"email": "operator@example.com"},
        format="json",
    )

    assert resp.status_code == 201
    assert "token" in resp.json()
    assert calls
    assert calls[0][0] == tenant
    assert calls[0][1] == "operator@example.com"
    assert calls[0][2] == resp.json()["token"]


@override_settings(DEBUG=False)
@pytest.mark.django_db
def test_invite_does_not_return_token_when_debug_off(monkeypatch):
    tenant = Tenant.objects.create(slug="t-invite2", name="T Invite2")
    admin = get_user_model().objects.create_user(username="admin2", password="pw")
    client = build_admin_client(tenant=tenant, user=admin)

    calls = []

    def fake_send(*, tenant, email, token, invited_by_user):
        calls.append((tenant, email, token, invited_by_user))

    monkeypatch.setattr("tenants.views.send_tenant_invite_email", fake_send)

    resp = client.post(
        "/api/tenant/invites/",
        data={"email": "operator2@example.com"},
        format="json",
    )

    assert resp.status_code == 201
    assert "token" not in resp.json()
    assert calls


@override_settings(DEBUG=True)
@pytest.mark.django_db
def test_invite_resend_sends_email_with_rotated_token(monkeypatch):
    tenant = Tenant.objects.create(slug="t-invite3", name="T Invite3")
    admin = get_user_model().objects.create_user(username="admin3", password="pw")
    client = build_admin_client(tenant=tenant, user=admin)

    calls = []

    def fake_send(*, tenant, email, token, invited_by_user):
        calls.append(token)

    monkeypatch.setattr("tenants.views.send_tenant_invite_email", fake_send)

    resp1 = client.post(
        "/api/tenant/invites/",
        data={"email": "operator3@example.com"},
        format="json",
    )
    resp2 = client.post(
        "/api/tenant/invites/",
        data={"email": "operator3@example.com"},
        format="json",
    )

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["token"] != resp2.json()["token"]
    assert len(calls) == 2
    assert calls[0] != calls[1]


@override_settings(DEBUG=False)
@pytest.mark.django_db
def test_invite_email_failure_does_not_rollback(monkeypatch):
    tenant = Tenant.objects.create(slug="t-invite4", name="T Invite4")
    admin = get_user_model().objects.create_user(username="admin4", password="pw")
    client = build_admin_client(tenant=tenant, user=admin)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("tenants.views.send_tenant_invite_email", boom)

    resp = client.post(
        "/api/tenant/invites/",
        data={"email": "operator4@example.com"},
        format="json",
    )

    assert resp.status_code == 201
    assert "token" not in resp.json()

    invite = TenantInvite.objects.get(tenant=tenant, email="operator4@example.com")
    event = TenantInviteEvent.objects.filter(
        tenant=tenant,
        email="operator4@example.com",
        event_type=TenantInviteEvent.EventType.CREATED,
    ).latest("created_at")
    assert invite is not None
    assert event.metadata == {"email_sent": False}
