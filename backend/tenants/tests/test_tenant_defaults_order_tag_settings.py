import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership


def build_client(*, tenant, user, role=TenantMembership.Role.OPERATOR) -> APIClient:
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
def test_defaults_get_includes_order_tag_print_fields():
    tenant = Tenant.objects.create(
        slug="t-defaults-print-get",
        name="T Defaults Print GET",
        order_tag_label_size=Tenant.OrderTagLabelSize.FOUR_BY_TWO,
        order_tag_copies=3,
    )
    user = get_user_model().objects.create_user(username="u-print-get", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.get("/api/tenant/defaults/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_tag_label_size"] == "4x2"
    assert data["order_tag_copies"] == 3


@pytest.mark.django_db
def test_defaults_patch_updates_order_tag_print_fields():
    tenant = Tenant.objects.create(
        slug="t-defaults-print-patch",
        name="T Defaults Print PATCH",
    )
    user = get_user_model().objects.create_user(
        username="u-print-patch", password="pw"
    )
    client = build_client(tenant=tenant, user=user)

    resp = client.patch(
        "/api/tenant/defaults/",
        data={"order_tag_label_size": "4x2", "order_tag_copies": 5},
        format="json",
    )
    assert resp.status_code == 200

    tenant.refresh_from_db()
    assert tenant.order_tag_label_size == "4x2"
    assert tenant.order_tag_copies == 5


@pytest.mark.django_db
def test_defaults_patch_rejects_invalid_order_tag_settings():
    tenant = Tenant.objects.create(
        slug="t-defaults-print-invalid",
        name="T Defaults Print Invalid",
    )
    user = get_user_model().objects.create_user(
        username="u-print-invalid", password="pw"
    )
    client = build_client(tenant=tenant, user=user)

    invalid_size_resp = client.patch(
        "/api/tenant/defaults/",
        data={"order_tag_label_size": "3x1"},
        format="json",
    )
    assert invalid_size_resp.status_code == 400
    assert "order_tag_label_size" in invalid_size_resp.json()

    invalid_copies_resp = client.patch(
        "/api/tenant/defaults/",
        data={"order_tag_copies": 0},
        format="json",
    )
    assert invalid_copies_resp.status_code == 400
    assert "order_tag_copies" in invalid_copies_resp.json()
