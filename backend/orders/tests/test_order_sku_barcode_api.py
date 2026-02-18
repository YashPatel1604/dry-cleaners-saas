import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from orders.models import Order
from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety


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
def test_receipt_contains_order_identity_and_barcode():
    tenant = Tenant.objects.create(slug="t-order-sku", name="Order SKU")
    user = get_user_model().objects.create_user(username="op-sku", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = Order.objects.create(tenant=tenant, status="RECEIVED")
    expected_sku = f"ORD-{order.id:08d}"
    expected_barcode_path = f"/api/orders/{order.id}/barcode.svg/"

    receipt_resp = client.get(f"/api/orders/{order.id}/receipt/")
    assert receipt_resp.status_code == 200
    receipt = receipt_resp.json()

    assert receipt["order_number"] == order.id
    assert receipt["order_sku"] == expected_sku
    assert receipt["barcode_value"] == expected_sku
    assert receipt["barcode_svg_path"] == expected_barcode_path
    assert receipt["barcode_svg_url"].endswith(expected_barcode_path)

    barcode_resp = client.get(expected_barcode_path)
    assert barcode_resp.status_code == 200
    assert barcode_resp["Content-Type"].startswith("image/svg+xml")
    assert barcode_resp.content.startswith(b"<?xml")


@pytest.mark.django_db
def test_cards_search_supports_order_sku():
    tenant = Tenant.objects.create(slug="t-order-cards-sku", name="Order Cards SKU")
    user = get_user_model().objects.create_user(username="op-cards", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    order = Order.objects.create(tenant=tenant, status="READY")
    expected_sku = f"ORD-{order.id:08d}"
    expected_barcode_path = f"/api/orders/{order.id}/barcode.svg/"

    resp = client.get(f"/api/orders/cards/?q={expected_sku}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert len(data["results"]) == 1

    card = data["results"][0]
    assert card["order_id"] == order.id
    assert card["order_sku"] == expected_sku
    assert card["barcode_svg_url"].endswith(expected_barcode_path)
