import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
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
def test_receipt_email_disabled_returns_501():
    tenant = Tenant.objects.create(slug="t-email-off", name="Email Off")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    order = Order.objects.create(tenant=tenant, status="RECEIVED")

    resp = client.post(f"/api/orders/{order.id}/receipt/email/", data={"to_email": "a@b.com"}, format="json")
    assert resp.status_code == 501


@pytest.mark.django_db
@override_settings(RECEIPT_EMAIL_ENABLED=True, DEFAULT_FROM_EMAIL="noreply@example.com")
def test_receipt_email_sends(monkeypatch):
    tenant = Tenant.objects.create(slug="t-email-on", name="Email On")
    user = get_user_model().objects.create_user(username="admin", password="pw")
    client = build_client(tenant=tenant, user=user, role=TenantMembership.Role.OWNER_ADMIN)

    customer = Customer.objects.create(tenant=tenant, name="Patel", email="patel@example.com")
    order = Order.objects.create(tenant=tenant, status="RECEIVED", customer=customer)

    captured = {}

    def fake_send_mail(subject, message, from_email, recipient_list, fail_silently):
        captured["subject"] = subject
        captured["message"] = message
        captured["from_email"] = from_email
        captured["recipient_list"] = recipient_list
        return 1

    monkeypatch.setattr("orders.views.send_mail", fake_send_mail)

    resp = client.post(f"/api/orders/{order.id}/receipt/email/", data={}, format="json")
    assert resp.status_code == 200
    assert captured["recipient_list"] == ["patel@example.com"]
