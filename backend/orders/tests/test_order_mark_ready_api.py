import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
from orders.models import Order, OrderStatusEvent

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
def test_mark_ready_operator_allowed_and_idempotent():
    tenant = Tenant.objects.create(slug="t-ready", name="Ready")
    user = get_user_model().objects.create_user(username="op", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OPERATOR)

    order = Order.objects.create(tenant=tenant, status="IN_PROGRESS")

    resp = client.post(f"/api/orders/{order.id}/mark_ready/")
    assert resp.status_code == 200

    order.refresh_from_db()
    assert order.status == "READY"
    assert order.ready_at is not None
    assert OrderStatusEvent.objects.filter(order=order, to_status="READY").count() == 1

    resp = client.post(f"/api/orders/{order.id}/mark_ready/")
    assert resp.status_code == 200
    assert OrderStatusEvent.objects.filter(order=order, to_status="READY").count() == 1


@pytest.mark.django_db
def test_mark_ready_blocked_when_settled():
    tenant = Tenant.objects.create(slug="t-ready-settled", name="Ready Settled")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    order = Order.objects.create(
        tenant=tenant,
        status="IN_PROGRESS",
        settled_at=timezone.now(),
        settled_total_cents=1000,
        settled_paid_cents=1000,
        settled_balance_due_cents=0,
    )

    resp = client.post(f"/api/orders/{order.id}/mark_ready/")
    assert resp.status_code == 400
