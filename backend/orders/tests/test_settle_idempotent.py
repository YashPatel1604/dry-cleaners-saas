import pytest

pytestmark = pytest.mark.operator_safety
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Tenant, TenantMembership
from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from payments.models import Payment


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
def test_settle_idempotent_replay_header(django_user_model):
    tenant = Tenant.objects.create(slug="t-settle", name="T Settle")
    user = django_user_model.objects.create_user(username="u-settle", password="pw")
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OWNER_ADMIN,
        is_active=True,
    )

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000005",
    )

    inv = create_inventory_item(tenant=tenant, name="Shirt", price_cents=1000)

    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="COMPLETED",
        due_at=timezone.now(),
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
        method=Payment.Method.CASH,
        status=Payment.Status.CAPTURED,
        direction=Payment.Direction.IN,
        amount_cents=1080,
        reference="p-settle-1",
    )

    api = APIClient()
    api.force_authenticate(user=user)
    api.credentials(HTTP_X_TENANT=tenant.slug)

    first = api.post(f"/api/orders/{order.id}/settle/", data={}, format="json")
    assert first.status_code == 200
    assert first.get("Idempotent-Replay") is None

    second = api.post(f"/api/orders/{order.id}/settle/", data={}, format="json")
    assert second.status_code == 200
    assert second.get("Idempotent-Replay") == "true"
