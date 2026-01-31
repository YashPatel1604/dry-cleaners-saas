import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership, TenantMembershipEvent, TenantConfigEvent

pytestmark = pytest.mark.operator_safety


@pytest.mark.django_db
def test_bootstrap_happy_path():
    user = get_user_model().objects.create_user(username="u1", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/tenant/bootstrap/",
        data={"slug": "demo-cleaners-3", "name": "Demo Cleaners 3"},
        format="json",
    )
    assert resp.status_code == 201

    tenant = Tenant.objects.get(slug="demo-cleaners-3")
    membership = TenantMembership.objects.get(tenant=tenant, user=user)
    assert membership.role == TenantMembership.Role.OWNER_ADMIN
    assert membership.is_active is True

    event = TenantMembershipEvent.objects.filter(tenant=tenant).latest("created_at")
    assert event.action == TenantMembershipEvent.Action.CREATED
    assert event.actor_id == user.id
    assert event.subject_user_id == user.id


@pytest.mark.django_db
def test_bootstrap_slug_exists():
    Tenant.objects.create(slug="demo-cleaners-3", name="Existing")
    user = get_user_model().objects.create_user(username="u2", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/tenant/bootstrap/",
        data={"slug": "demo-cleaners-3", "name": "Duplicate"},
        format="json",
    )
    assert resp.status_code == 409
    assert TenantMembership.objects.filter(user=user).count() == 0
    assert TenantMembershipEvent.objects.count() == 0


@pytest.mark.django_db
def test_bootstrap_invalid_slug():
    user = get_user_model().objects.create_user(username="u3", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/tenant/bootstrap/",
        data={"slug": "Bad Slug", "name": "Bad"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_bootstrap_optional_fields():
    user = get_user_model().objects.create_user(username="u4", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/tenant/bootstrap/",
        data={
            "slug": "demo-cleaners-4",
            "name": "Demo Cleaners 4",
            "tax_enabled": False,
            "tax_rate_bps": 850,
            "require_paid_in_full_at_pickup": False,
            "default_ready_hour": 9,
            "default_due_days": 3,
        },
        format="json",
    )
    assert resp.status_code == 201

    tenant = Tenant.objects.get(slug="demo-cleaners-4")
    assert tenant.collects_tax is False
    assert tenant.tax_rate_bps == 850
    assert tenant.require_paid_in_full_at_pickup is False
    assert tenant.default_ready_hour == 9
    assert tenant.default_turnaround_days == 3

    assert TenantConfigEvent.objects.filter(tenant=tenant).exists()
