import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import PasswordResetEvent
from tenants.models import PasswordResetToken
from tenants.utils import generate_token, hash_token


@pytest.mark.django_db
def test_password_reset_request_unknown_email_returns_200():
    client = APIClient(raise_request_exception=False)
    resp = client.post(
        "/api/auth/password-reset/request/",
        data={"email": "missing@example.com"},
        format="json",
    )

    assert resp.status_code == 200
    assert PasswordResetToken.objects.count() == 0


@pytest.mark.django_db
def test_password_reset_request_known_email_creates_token():
    user = get_user_model().objects.create_user(
        username="u-reset", email="reset@example.com", password="old"
    )

    client = APIClient(raise_request_exception=False)
    resp = client.post(
        "/api/auth/password-reset/request/",
        data={"email": "reset@example.com"},
        format="json",
    )

    assert resp.status_code == 200
    assert PasswordResetToken.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_password_reset_confirm_valid_token_sets_password_and_marks_used():
    user = get_user_model().objects.create_user(
        username="u-confirm", email="confirm@example.com", password="old"
    )
    raw_token = generate_token()
    reset_token = PasswordResetToken.objects.create(
        user=user,
        token_hash=hash_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    client = APIClient(raise_request_exception=False)
    resp = client.post(
        "/api/auth/password-reset/confirm/",
        data={"token": raw_token, "new_password": "newpass123"},
        format="json",
    )

    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.check_password("newpass123")

    reset_token.refresh_from_db()
    assert reset_token.used_at is not None
    assert PasswordResetEvent.objects.filter(
        email="confirm@example.com",
        event_type=PasswordResetEvent.EventType.CONFIRMED,
    ).exists()


@pytest.mark.django_db
def test_password_reset_confirm_invalid_tokens_return_400():
    user = get_user_model().objects.create_user(
        username="u-invalid", email="invalid@example.com", password="old"
    )
    expired_token = generate_token()
    used_token = generate_token()
    PasswordResetToken.objects.create(
        user=user,
        token_hash=hash_token(expired_token),
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    used_row = PasswordResetToken.objects.create(
        user=user,
        token_hash=hash_token(used_token),
        expires_at=timezone.now() + timedelta(minutes=30),
        used_at=timezone.now() - timedelta(minutes=1),
    )

    client = APIClient(raise_request_exception=False)
    for token in (expired_token, used_token):
        resp = client.post(
            "/api/auth/password-reset/confirm/",
            data={"token": token, "new_password": "newpass123"},
            format="json",
        )
        assert resp.status_code == 400

    user.refresh_from_db()
    assert user.check_password("old")
    used_row.refresh_from_db()
    assert used_row.used_at is not None


@pytest.mark.django_db
def test_password_reset_confirm_transactional_behavior(monkeypatch):
    user = get_user_model().objects.create_user(
        username="u-tx", email="tx@example.com", password="old"
    )
    raw_token = generate_token()
    reset_token = PasswordResetToken.objects.create(
        user=user,
        token_hash=hash_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("accounts.views.PasswordResetEvent.objects.create", boom)

    client = APIClient(raise_request_exception=False)
    resp = client.post(
        "/api/auth/password-reset/confirm/",
        data={"token": raw_token, "new_password": "newpass123"},
        format="json",
    )
    assert resp.status_code == 500

    user.refresh_from_db()
    reset_token.refresh_from_db()
    assert user.check_password("old")
    assert reset_token.used_at is None
