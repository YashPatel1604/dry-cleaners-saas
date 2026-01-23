import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
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


@pytest.mark.django_db
def test_order_cards_basic_and_filters():
    tenant = Tenant.objects.create(slug="t-cards", name="Cards")
    user = get_user_model().objects.create_user(username="op", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OPERATOR)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Alice",
        phone="7145551212",
        email="alice@example.com",
    )

    order1 = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="READY",
        total_cents=1000,
        paid_cents=500,
    )
    Order.objects.create(tenant=tenant, status="RECEIVED")

    resp = client.get("/api/orders/cards/?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2

    card = next(row for row in data["results"] if row["order_id"] == order1.id)
    assert card["customer"]["name"] == "Alice"
    assert card["customer"]["email"] == "alice@example.com"

    resp = client.get(f"/api/orders/cards/?q=alice@example.com")
    assert resp.status_code == 200
    ids = {row["order_id"] for row in resp.json()["results"]}
    assert order1.id in ids

    resp = client.get(f"/api/orders/cards/?q={order1.id}")
    assert resp.status_code == 200
    ids = {row["order_id"] for row in resp.json()["results"]}
    assert order1.id in ids


@pytest.mark.django_db
def test_order_cards_query_count(django_assert_num_queries):
    tenant = Tenant.objects.create(slug="t-cards-qc", name="Cards QC")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    customer = Customer.objects.create(tenant=tenant, name="Patel")
    for _ in range(3):
        Order.objects.create(tenant=tenant, customer=customer, status="READY")

    with django_assert_num_queries(8, exact=False):
        resp = client.get("/api/orders/cards/?limit=5")
    assert resp.status_code == 200
