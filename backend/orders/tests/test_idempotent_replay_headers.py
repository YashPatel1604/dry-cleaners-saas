import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
from payments.models import Payment
from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety


def build_client(
    *,
    tenant,
    user,
    role=TenantMembership.Role.OWNER_ADMIN,
    is_active: bool = True,
) -> APIClient:
    membership, created = TenantMembership.objects.get_or_create(
        tenant=tenant,
        user=user,
        defaults={"role": role, "is_active": is_active},
    )
    if not created and (membership.role != role or membership.is_active != is_active):
        membership.role = role
        membership.is_active = is_active
        membership.save(update_fields=["role", "is_active"])
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


@pytest.mark.django_db
def test_pickup_payment_replay_header(django_user_model):
    tenant = Tenant.objects.create(slug="t-pickup-pay", name="T Pickup Pay")
    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000020",
    )

    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="READY",
        due_at=timezone.now(),
    )

    payload = {
        "amount_cents": 1500,
        "method": "CASH",
        "reference": "pickup-pay-1",
        "note": "overpay",
    }

    first = client.post(
        f"/api/orders/{order.id}/pickup-payment/",
        data=payload,
        format="json",
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/orders/{order.id}/pickup-payment/",
        data=payload,
        format="json",
    )
    assert second.status_code == 200
    assert second.get("Idempotent-Replay") == "true"

    first_data = first.json()
    second_data = second.json()

    assert set(first_data.keys()) == {"payment", "change_payment", "order"}
    assert set(second_data.keys()) == {"payment", "change_payment", "order"}
    assert second_data["payment"]["id"] == first_data["payment"]["id"]
    if first_data["change_payment"] is not None:
        assert second_data["change_payment"]["id"] == first_data["change_payment"]["id"]


@pytest.mark.django_db
def test_cash_out_replay_header(django_user_model):
    tenant = Tenant.objects.create(slug="t-cash-out", name="T Cash Out")
    user = django_user_model.objects.create_user(username="u2", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000021",
    )

    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="READY",
        due_at=timezone.now(),
    )

    payload = {
        "amount_cents": 200,
        "method": "CASH",
        "reference": "cash-out-1",
        "note": "refund",
    }

    first = client.post(
        f"/api/orders/{order.id}/cash-out/",
        data=payload,
        format="json",
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/orders/{order.id}/cash-out/",
        data=payload,
        format="json",
    )
    assert second.status_code == 200
    assert second.get("Idempotent-Replay") == "true"

    first_data = first.json()
    second_data = second.json()

    assert "payment_out" in first_data
    assert "order" in first_data
    assert "id" in second_data
    assert second_data["id"] == first_data["payment_out"]["id"]


@pytest.mark.django_db
def test_pickup_replay_header(django_user_model):
    tenant = Tenant.objects.create(slug="t-pickup", name="T Pickup")
    user = django_user_model.objects.create_user(username="u3", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000022",
    )

    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="READY",
        due_at=timezone.now(),
    )

    first = client.post(f"/api/orders/{order.id}/pickup/", data={}, format="json")
    assert first.status_code == 200

    second = client.post(f"/api/orders/{order.id}/pickup/", data={}, format="json")
    assert second.status_code == 200
    assert second.get("Idempotent-Replay") == "true"
    assert second.json() == first.json()


@pytest.mark.django_db
def test_settle_replay_header(django_user_model):
    tenant = Tenant.objects.create(slug="t-settle", name="T Settle")
    user = django_user_model.objects.create_user(username="u4", password="pw")
    client = build_client(tenant=tenant, user=user)

    customer = Customer.objects.create(
        tenant=tenant,
        name="Patel",
        phone="7140000023",
    )

    order = Order.objects.create(
        tenant=tenant,
        customer=customer,
        status="COMPLETED",
        due_at=timezone.now(),
    )

    first = client.post(f"/api/orders/{order.id}/settle/", data={}, format="json")
    assert first.status_code == 200

    second = client.post(f"/api/orders/{order.id}/settle/", data={}, format="json")
    assert second.status_code == 200
    assert second.get("Idempotent-Replay") == "true"
    assert second.json() == first.json()
