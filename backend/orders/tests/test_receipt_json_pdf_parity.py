import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from payments.models import Payment
from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety


def create_inventory_item(*, tenant, name: str, price_cents: int) -> InventoryItem:
    item = InventoryItem(tenant=tenant, name=name)

    field_names = {f.name for f in InventoryItem._meta.get_fields()
                   if hasattr(f, "attname")}
    candidates = [
        "price_cents",
        "unit_price_cents",
        "default_price_cents",
        "base_price_cents",
        "price",
        "base_price",
    ]

    for fname in candidates:
        if fname in field_names:
            setattr(item, fname, price_cents)
            item.save()
            return item

    raise AssertionError(
        f"Could not find a price field on InventoryItem. Fields: {sorted(field_names)}")


@pytest.mark.django_db
def test_receipt_json_matches_print_presenter(django_user_model, monkeypatch):
    tenant = Tenant.objects.create(slug="t-parity", name="T Parity")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    )

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000040",
    )

    inv = create_inventory_item(tenant=tenant, name="Shirt", price_cents=1000)

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
        unit_price_cents=1000,
        line_total_cents=1000,
    )

    Payment.objects.create(
        tenant=tenant,
        order=order,
        method=Payment.Method.CARD,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=500,
        reference="p-parity",
    )

    captured = {}

    def fake_render(receipt_dict):
        captured["receipt"] = receipt_dict
        return b"%PDF-FAKE%"

    monkeypatch.setattr("orders.views.render_receipt_pdf", fake_render)

    api = APIClient()
    api.force_authenticate(user=user)
    api.credentials(HTTP_X_TENANT=tenant.slug)

    receipt_resp = api.get(f"/api/orders/{order.id}/receipt/")
    assert receipt_resp.status_code == 200
    receipt_json = receipt_resp.json()

    print_resp = api.get(f"/api/orders/{order.id}/receipt/print/")
    assert print_resp.status_code == 200
    assert print_resp.content == b"%PDF-FAKE%"

    assert captured.get("receipt") == receipt_json
