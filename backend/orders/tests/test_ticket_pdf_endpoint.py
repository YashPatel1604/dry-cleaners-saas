import pytest
from django.contrib.auth import get_user_model
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
def test_ticket_pdf_returns_pdf():
    tenant = Tenant.objects.create(slug="t-ticket", name="Ticket")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    order = Order.objects.create(tenant=tenant, status="RECEIVED")

    resp = client.get(f"/api/orders/{order.id}/ticket.pdf/")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("application/pdf")
