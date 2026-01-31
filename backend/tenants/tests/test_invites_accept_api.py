import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantInvite, TenantInviteEvent, TenantMembership, TenantMembershipEvent
from tenants.utils import generate_invite_token, hash_invite_token

pytestmark = pytest.mark.operator_safety


def create_invite(*, tenant, email, expires_at, accepted_at=None, revoked_at=None):
    token = generate_invite_token()
    invite = TenantInvite.objects.create(
        tenant=tenant,
        email=email,
        role=TenantInvite.Role.OPERATOR,
        token_hash=hash_invite_token(token),
        expires_at=expires_at,
        accepted_at=accepted_at,
        revoked_at=revoked_at,
    )
    return invite, token


@pytest.mark.django_db
def test_accept_creates_user_membership_and_events():
    tenant = Tenant.objects.create(slug="t-acc", name="T Acc")
    invite, token = create_invite(
        tenant=tenant,
        email="Invitee@Email.com",
        expires_at=timezone.now() + timedelta(days=3),
    )

    client = APIClient(raise_request_exception=False)
    resp = client.post(
        "/api/invites/accept/",
        data={"token": token, "password": "p@ssw0rd"},
        format="json",
    )
    assert resp.status_code == 200

    user = get_user_model().objects.get(email="invitee@email.com")
    membership = TenantMembership.objects.get(tenant=tenant, user=user)
    assert membership.is_active is True
    assert membership.role == TenantMembership.Role.OPERATOR

    invite.refresh_from_db()
    assert invite.accepted_at is not None
    assert TenantInviteEvent.objects.filter(
        tenant=tenant,
        email="invitee@email.com",
        event_type=TenantInviteEvent.EventType.ACCEPTED,
    ).exists()
    assert TenantMembershipEvent.objects.filter(
        tenant=tenant,
        subject_user=user,
        action=TenantMembershipEvent.Action.CREATED,
    ).exists()


@pytest.mark.django_db
def test_accept_existing_user_sets_password_and_membership():
    tenant = Tenant.objects.create(slug="t-acc2", name="T Acc2")
    user = get_user_model().objects.create_user(
        username="u1", email="user@example.com", password="old"
    )
    invite, token = create_invite(
        tenant=tenant,
        email="user@example.com",
        expires_at=timezone.now() + timedelta(days=2),
    )

    client = APIClient(raise_request_exception=False)
    resp = client.post(
        "/api/invites/accept/",
        data={"token": token, "password": "newpass"},
        format="json",
    )
    assert resp.status_code == 200

    user.refresh_from_db()
    assert user.check_password("newpass")
    assert TenantMembership.objects.filter(tenant=tenant, user=user).exists()


@pytest.mark.django_db
def test_accept_existing_inactive_membership_activates():
    tenant = Tenant.objects.create(slug="t-acc3", name="T Acc3")
    user = get_user_model().objects.create_user(
        username="u2", email="inactive@example.com", password="old"
    )
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OPERATOR,
        is_active=False,
    )
    invite, token = create_invite(
        tenant=tenant,
        email="inactive@example.com",
        expires_at=timezone.now() + timedelta(days=2),
    )

    client = APIClient(raise_request_exception=False)
    resp = client.post(
        "/api/invites/accept/",
        data={"token": token, "password": "newpass"},
        format="json",
    )
    assert resp.status_code == 200

    membership = TenantMembership.objects.get(tenant=tenant, user=user)
    assert membership.is_active is True
    assert TenantMembershipEvent.objects.filter(
        tenant=tenant,
        subject_user=user,
        action=TenantMembershipEvent.Action.REACTIVATED,
    ).exists()


@pytest.mark.django_db
def test_accept_expired_revoked_or_accepted_rejected():
    tenant = Tenant.objects.create(slug="t-acc4", name="T Acc4")
    expired_invite, expired_token = create_invite(
        tenant=tenant,
        email="expired@example.com",
        expires_at=timezone.now() - timedelta(days=1),
    )
    revoked_invite, revoked_token = create_invite(
        tenant=tenant,
        email="revoked@example.com",
        expires_at=timezone.now() + timedelta(days=1),
        revoked_at=timezone.now(),
    )
    accepted_invite, accepted_token = create_invite(
        tenant=tenant,
        email="accepted@example.com",
        expires_at=timezone.now() + timedelta(days=1),
        accepted_at=timezone.now(),
    )

    client = APIClient(raise_request_exception=False)
    for token in (expired_token, revoked_token, accepted_token):
        resp = client.post(
            "/api/invites/accept/",
            data={"token": token, "password": "x"},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
def test_accept_transactional_behavior(monkeypatch):
    tenant = Tenant.objects.create(slug="t-acc5", name="T Acc5")
    invite, token = create_invite(
        tenant=tenant,
        email="boom@example.com",
        expires_at=timezone.now() + timedelta(days=1),
    )

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("tenants.views.record_membership_event", boom)

    client = APIClient(raise_request_exception=False)
    resp = client.post(
        "/api/invites/accept/",
        data={"token": token, "password": "x"},
        format="json",
    )
    assert resp.status_code == 500

    assert get_user_model().objects.filter(email="boom@example.com").count() == 0
    invite.refresh_from_db()
    assert invite.accepted_at is None
    assert TenantMembership.objects.filter(tenant=tenant).count() == 0
