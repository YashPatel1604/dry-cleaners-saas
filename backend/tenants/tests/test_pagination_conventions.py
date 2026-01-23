import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership, TenantInvite
from customers.models import Customer
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


def assert_list_paginated(resp, *, limit: int):
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= limit


@pytest.mark.django_db
def test_pagination_conventions_across_endpoints():
    tenant = Tenant.objects.create(slug="t-page", name="Page")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    for i in range(10):
        Customer.objects.create(tenant=tenant, name=f"Test Customer {i}")

    resp = client.get("/api/tenant/customers/search/?q=Test&limit=3&offset=1")
    assert_list_paginated(resp, limit=3)

    customer = Customer.objects.create(tenant=tenant, name="Patel")
    for _ in range(6):
        Order.objects.create(tenant=tenant, customer=customer, status="RECEIVED")

    resp = client.get("/api/orders/search/?q=Patel&limit=2&offset=0")
    assert_list_paginated(resp, limit=2)

    now = timezone.now()
    for i in range(5):
        TenantInvite.objects.create(
            tenant=tenant,
            email=f"u{i}@example.com",
            token_hash="x",
            expires_at=now,
            created_by=user,
        )

    resp = client.get("/api/tenant/invites/?limit=2&offset=1")
    assert_list_paginated(resp, limit=2)
