from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from tenants.models import Tenant, TenantMembership


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
def test_dashboard_summary_uses_daily_invoice_and_piece_totals():
    tenant = Tenant.objects.create(slug="t-dashboard", name="Dashboard")
    user = get_user_model().objects.create_user(username="dash", password="pw")
    client = build_client(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OPERATOR,
    )

    item = InventoryItem.objects.create(
        tenant=tenant,
        name="Shirt",
        sku="INV-1",
        unit_price_cents=1000,
    )

    order_today = Order.objects.create(tenant=tenant, status="RECEIVED")
    OrderItem.objects.create(
        tenant=tenant,
        order=order_today,
        item=item,
        quantity=3,
        unit_price_cents=1000,
    )
    OrderItem.objects.create(
        tenant=tenant,
        order=order_today,
        item=item,
        quantity=2,
        unit_price_cents=1000,
    )

    cancelled_today = Order.objects.create(tenant=tenant, status="CANCELLED")
    OrderItem.objects.create(
        tenant=tenant,
        order=cancelled_today,
        item=item,
        quantity=9,
        unit_price_cents=1000,
    )

    old_order = Order.objects.create(tenant=tenant, status="RECEIVED")
    yesterday = timezone.now() - timedelta(days=1)
    Order.objects.filter(id=old_order.id).update(created_at=yesterday)
    old_order.refresh_from_db(fields=["created_at"])
    OrderItem.objects.create(
        tenant=tenant,
        order=old_order,
        item=item,
        quantity=7,
        unit_price_cents=1000,
    )

    resp = client.get("/api/dashboard/summary/")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["orders_today"] == 1
    assert payload["pieces_today"] == 5
