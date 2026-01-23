# orders/tests/test_receipt_print_endpoint.py
from orders.services import recalc_order_totals
import pytest

pytestmark = pytest.mark.operator_safety
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from payments.models import Payment

from orders.services import ReceiptPresenter


@pytest.mark.django_db
def test_receipt_print_returns_pdf(django_user_model):
    tenant = Tenant.objects.create(slug="t-print", name="T Print")
    user = django_user_model.objects.create_user(
        username="u1", password="pw123")
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    )

    customer = Customer.objects.create(
        tenant=tenant,
        name="John Doe",
        phone="714-555-0101",
        email="john@example.com",
    )

    inv = InventoryItem.objects.create(
        tenant=tenant,
        name="Shirt",
        sku="SHIRT",
        unit_price_cents=500,
    )

    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        received_at=timezone.now(),
    )
    OrderItem.objects.create(
        tenant=tenant,
        order=order,
        item=inv,
        quantity=2,
        unit_price_cents=inv.unit_price_cents,
    )

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=500,
        reference="p1",
        note="test",
    )

    api = APIClient()
    api.force_authenticate(user=user)

    resp = api.get(
        f"/api/orders/{order.id}/receipt/print/",
        HTTP_X_TENANT=tenant.slug,
    )

    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("application/pdf")
    assert "Content-Disposition" in resp


@pytest.mark.django_db
def test_receipt_print_uses_presenter_payload(django_user_model, monkeypatch):
    tenant = Tenant.objects.create(slug="t-print2", name="T Print2")
    user = django_user_model.objects.create_user(
        username="u2", password="pw123")
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    )

    customer = Customer.objects.create(
        tenant=tenant,
        name="Jane Doe",
        phone="949-555-0101",
        email="jane@example.com",
    )

    inv = InventoryItem.objects.create(
        tenant=tenant,
        name="Pants",
        sku="PANTS",
        unit_price_cents=1200,
    )

    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="RECEIVED",
        received_at=timezone.now(),
    )
    OrderItem.objects.create(
        tenant=tenant,
        order=order,
        item=inv,
        quantity=1,
        unit_price_cents=inv.unit_price_cents,
    )

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1000,
        reference="p2",
        note="test",
    )

    captured = {}

    def fake_render(receipt_dict):
        captured["receipt"] = receipt_dict
        return b"%PDF-FAKE%"

    monkeypatch.setattr("orders.views.render_receipt_pdf", fake_render)

    api = APIClient()
    api.force_authenticate(user=user)

    resp = api.get(
        f"/api/orders/{order.id}/receipt/print/",
        HTTP_X_TENANT=tenant.slug,
    )

    assert resp.status_code == 200
    assert resp.content == b"%PDF-FAKE%"

    recalc_order_totals(order)
    order.refresh_from_db(
        fields=["subtotal_cents", "tax_cents", "total_cents", "paid_cents", "settled_at"])

    expected = ReceiptPresenter(order).build()
    expected["pdf_url"] = resp.wsgi_request.build_absolute_uri(
        f"/api/orders/{order.id}/receipt/print/"
    )
    assert captured["receipt"] == expected
