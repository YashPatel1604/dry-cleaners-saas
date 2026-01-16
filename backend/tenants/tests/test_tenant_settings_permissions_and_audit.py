import pytest
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from tenants.models import Tenant, TenantConfigEvent, TenantMembership

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
def test_operator_cannot_patch_settings():
    tenant = Tenant.objects.create(slug="t-settings-op", name="T Settings Op")
    user = get_user_model().objects.create_user(username="u1", password="pw")
    client = build_client(
        tenant=tenant, user=user, role=TenantMembership.Role.OPERATOR
    )

    resp = client.patch(
        "/api/tenant/settings/",
        data={"tax_rate_bps": 500},
        format="json",
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_admin_can_patch_settings_and_audit():
    tenant = Tenant.objects.create(
        slug="t-settings-admin",
        name="T Settings Admin",
        collects_tax=True,
        tax_rate_bps=800,
    )
    user = get_user_model().objects.create_user(username="u2", password="pw")
    client = build_client(
        tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN
    )

    resp = client.patch(
        "/api/tenant/settings/",
        data={"collects_tax": False, "tax_rate_bps": 0},
        format="json",
    )
    assert resp.status_code == 200

    tenant.refresh_from_db()
    assert tenant.collects_tax is False
    assert tenant.tax_rate_bps == 0

    events = TenantConfigEvent.objects.filter(tenant=tenant).order_by("created_at")
    assert events.count() == 2
    keys = {e.key for e in events}
    assert keys == {"collects_tax", "tax_rate_bps"}

    for event in events:
        assert event.actor_id == user.id
        assert event.old_value != event.new_value


@pytest.mark.django_db
def test_settings_validation_rejects_invalid_bps():
    tenant = Tenant.objects.create(slug="t-settings-val", name="T Settings Val")
    user = get_user_model().objects.create_user(username="u3", password="pw")
    client = build_client(
        tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN
    )

    resp = client.patch(
        "/api/tenant/settings/",
        data={"tax_rate_bps": 2500},
        format="json",
    )
    assert resp.status_code == 400
