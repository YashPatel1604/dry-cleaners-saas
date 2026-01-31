import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
from orders.models import Order

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
def test_order_notes_create_and_list():
    tenant = Tenant.objects.create(slug="t-notes", name="Notes")
    user = get_user_model().objects.create_user(username="op", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OPERATOR)

    order = Order.objects.create(tenant=tenant, status="RECEIVED")

    resp = client.post(
        f"/api/orders/{order.id}/notes/",
        data={"note": "Handle with care"},
        format="json",
    )
    assert resp.status_code == 201

    resp = client.get(f"/api/orders/{order.id}/notes/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["note"] == "Handle with care"


@pytest.mark.django_db
def test_order_notes_allowed_after_settlement():
    tenant = Tenant.objects.create(slug="t-notes-settled", name="Notes Settled")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    order = Order.objects.create(
        tenant=tenant,
        status="PICKED_UP",
        settled_at=timezone.now(),
        settled_total_cents=1000,
        settled_paid_cents=1000,
        settled_balance_due_cents=0,
    )

    resp = client.post(
        f"/api/orders/{order.id}/notes/",
        data={"note": "Post-settlement note"},
        format="json",
    )
    assert resp.status_code == 201


@pytest.mark.django_db
def test_order_notes_non_member_404():
    tenant = Tenant.objects.create(slug="t-notes-out", name="Notes Out")
    user = get_user_model().objects.create_user(username="outsider", password="pw")
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)

    order = Order.objects.create(tenant=tenant, status="RECEIVED")

    resp = client.get(f"/api/orders/{order.id}/notes/")
    assert resp.status_code == 404
