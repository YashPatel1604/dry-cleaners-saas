import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from orders.models import Order, StorageLocation
from tenants.models import Tenant, TenantMembership

pytestmark = pytest.mark.operator_safety


def build_client(*, tenant, user) -> APIClient:
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role=TenantMembership.Role.OPERATOR,
        is_active=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_TENANT=tenant.slug)
    return client


@pytest.mark.django_db
def test_storage_location_lookup_reports_missing_barcode():
    tenant = Tenant.objects.create(slug="t-loc-lookup", name="T Loc Lookup")
    user = get_user_model().objects.create_user(username="loc-lookup", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.post(
        "/api/orders/storage-locations/lookup/",
        data={"barcode": "LOC-A1"},
        format="json",
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "barcode": "LOC-A1",
        "exists": False,
        "rack_number": None,
    }


@pytest.mark.django_db
def test_storage_location_lookup_rejects_invalid_barcode_format():
    tenant = Tenant.objects.create(slug="t-loc-invalid-lookup", name="T Loc Invalid Lookup")
    user = get_user_model().objects.create_user(username="loc-invalid-lookup", password="pw")
    client = build_client(tenant=tenant, user=user)

    resp = client.post(
        "/api/orders/storage-locations/lookup/",
        data={"barcode": "RACK-1"},
        format="json",
    )

    assert resp.status_code == 400
    assert "Invalid location barcode" in resp.json()["barcode"]


@pytest.mark.django_db
def test_assign_storage_location_by_order_sku_creates_location():
    tenant = Tenant.objects.create(slug="t-loc-assign", name="T Loc Assign")
    user = get_user_model().objects.create_user(username="loc-assign", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = Order.objects.create(tenant=tenant, status="READY")
    sku = f"ORD-{order.id:08d}"

    resp = client.post(
        "/api/orders/storage-locations/assign/",
        data={
            "location_barcode": "LOC-A1",
            "order_barcode": sku,
            "rack_number": "12",
        },
        format="json",
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["order_id"] == order.id
    assert payload["order_sku"] == sku
    assert payload["location_barcode"] == "LOC-A1"
    assert payload["rack_number"] == "12"
    assert payload["location_created"] is True
    assert payload["cleared_orders"] == 0
    assert payload["assigned_at"] is not None

    order.refresh_from_db()
    assert order.storage_location is not None
    assert order.storage_location.barcode == "LOC-A1"
    assert order.storage_location.rack_number == "12"
    assert order.storage_assigned_at is not None


@pytest.mark.django_db
def test_assign_storage_location_rack_number_is_optional():
    tenant = Tenant.objects.create(slug="t-loc-optional", name="T Loc Optional")
    user = get_user_model().objects.create_user(username="loc-optional", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = Order.objects.create(tenant=tenant, status="READY")

    sku = f"ORD-{order.id:08d}"

    resp = client.post(
        "/api/orders/storage-locations/assign/",
        data={
            "location_barcode": "LOC-B2",
            "order_barcode": sku,
        },
        format="json",
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["location_barcode"] == "LOC-B2"
    assert payload["rack_number"] is None
    assert payload["cleared_orders"] == 0

    location = StorageLocation.objects.get(tenant=tenant, barcode="LOC-B2")
    assert location.rack_number == ""


@pytest.mark.django_db
def test_assign_storage_location_rejects_when_rack_is_occupied():
    tenant = Tenant.objects.create(slug="t-loc-occupied", name="T Loc Occupied")
    user = get_user_model().objects.create_user(username="loc-occupied", password="pw")
    client = build_client(tenant=tenant, user=user)

    first_order = Order.objects.create(tenant=tenant, status="READY")
    second_order = Order.objects.create(tenant=tenant, status="READY")

    first_sku = f"ORD-{first_order.id:08d}"
    second_sku = f"ORD-{second_order.id:08d}"

    first_assign = client.post(
        "/api/orders/storage-locations/assign/",
        data={
            "location_barcode": "LOC-Z1",
            "order_barcode": first_sku,
            "rack_number": "3",
        },
        format="json",
    )
    assert first_assign.status_code == 200

    conflict = client.post(
        "/api/orders/storage-locations/assign/",
        data={
            "location_barcode": "LOC-Z1",
            "order_barcode": second_sku,
        },
        format="json",
    )

    assert conflict.status_code == 409
    payload = conflict.json()
    assert payload["code"] == "storage_location_occupied"
    assert payload["detail"] == "Rack already full."
    assert payload["location_barcode"] == "LOC-Z1"
    assert payload["current_order_id"] == first_order.id
    assert payload["current_order_sku"] == f"ORD-{first_order.id:08d}"

    second_order.refresh_from_db()
    assert second_order.storage_location is None


@pytest.mark.django_db
def test_assign_storage_location_with_force_clear_replaces_existing_order():
    tenant = Tenant.objects.create(slug="t-loc-force", name="T Loc Force")
    user = get_user_model().objects.create_user(username="loc-force", password="pw")
    client = build_client(tenant=tenant, user=user)

    first_order = Order.objects.create(tenant=tenant, status="READY")
    second_order = Order.objects.create(tenant=tenant, status="READY")

    first_sku = f"ORD-{first_order.id:08d}"
    second_sku = f"ORD-{second_order.id:08d}"

    first_assign = client.post(
        "/api/orders/storage-locations/assign/",
        data={
            "location_barcode": "LOC-Z2",
            "order_barcode": first_sku,
            "rack_number": "9",
        },
        format="json",
    )
    assert first_assign.status_code == 200

    second_assign = client.post(
        "/api/orders/storage-locations/assign/",
        data={
            "location_barcode": "LOC-Z2",
            "order_barcode": second_sku,
            "force_clear": True,
        },
        format="json",
    )
    assert second_assign.status_code == 200
    payload = second_assign.json()
    assert payload["order_id"] == second_order.id
    assert payload["location_barcode"] == "LOC-Z2"
    assert payload["cleared_orders"] == 1

    first_order.refresh_from_db()
    second_order.refresh_from_db()
    assert first_order.storage_location is None
    assert second_order.storage_location is not None


@pytest.mark.django_db
def test_pickup_with_clear_location_flag_clears_assigned_location():
    tenant = Tenant.objects.create(slug="t-loc-pickup", name="T Loc Pickup")
    user = get_user_model().objects.create_user(username="loc-pickup", password="pw")
    client = build_client(tenant=tenant, user=user)

    location = StorageLocation.objects.create(
        tenant=tenant, barcode="LOC-C3", rack_number="5"
    )
    order = Order.objects.create(
        tenant=tenant,
        status="READY",
        storage_location=location,
        storage_assigned_at=timezone.now(),
    )

    resp = client.post(
        f"/api/orders/{order.id}/pickup/",
        data={"clear_location": True},
        format="json",
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "PICKED_UP"

    order.refresh_from_db()
    assert order.storage_location is None
    assert order.storage_assigned_at is None


@pytest.mark.django_db
def test_assign_storage_location_rejects_invalid_order_barcode_format():
    tenant = Tenant.objects.create(slug="t-loc-invalid-order", name="T Loc Invalid Order")
    user = get_user_model().objects.create_user(username="loc-invalid-order", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = Order.objects.create(tenant=tenant, status="READY")
    assert order.id is not None

    resp = client.post(
        "/api/orders/storage-locations/assign/",
        data={
            "location_barcode": "LOC-X1",
            "order_barcode": str(order.id),
        },
        format="json",
    )

    assert resp.status_code == 400
    assert "Invalid order barcode" in resp.json()["order_barcode"]


@pytest.mark.django_db
def test_storage_location_status_returns_occupied_and_empty_locations():
    tenant = Tenant.objects.create(slug="t-loc-status", name="T Loc Status")
    user = get_user_model().objects.create_user(username="loc-status", password="pw")
    client = build_client(tenant=tenant, user=user)

    occupied_location = StorageLocation.objects.create(
        tenant=tenant, barcode="LOC-STATUS-1", rack_number="1"
    )
    empty_location = StorageLocation.objects.create(
        tenant=tenant, barcode="LOC-STATUS-2", rack_number="2"
    )
    order = Order.objects.create(
        tenant=tenant,
        status="READY",
        storage_location=occupied_location,
        storage_assigned_at=timezone.now(),
    )

    resp = client.get("/api/orders/storage-locations/status/")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] == 2

    by_barcode = {entry["location_barcode"]: entry for entry in payload["results"]}
    assert by_barcode["LOC-STATUS-1"]["occupied"] is True
    assert by_barcode["LOC-STATUS-1"]["current_order_id"] == order.id
    assert by_barcode["LOC-STATUS-1"]["current_order_sku"] == f"ORD-{order.id:08d}"
    assert by_barcode["LOC-STATUS-2"]["occupied"] is False
    assert by_barcode["LOC-STATUS-2"]["current_order_id"] is None
    assert by_barcode["LOC-STATUS-2"]["rack_number"] == empty_location.rack_number


@pytest.mark.django_db
def test_storage_location_history_tracks_assign_and_clear_events():
    tenant = Tenant.objects.create(slug="t-loc-history", name="T Loc History")
    user = get_user_model().objects.create_user(username="loc-history", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = Order.objects.create(tenant=tenant, status="READY")
    sku = f"ORD-{order.id:08d}"

    assign_resp = client.post(
        "/api/orders/storage-locations/assign/",
        data={
            "location_barcode": "LOC-H1",
            "order_barcode": sku,
            "rack_number": "7",
        },
        format="json",
    )
    assert assign_resp.status_code == 200

    clear_resp = client.post(
        f"/api/orders/{order.id}/storage-location/clear/",
        data={},
        format="json",
    )
    assert clear_resp.status_code == 200

    history_resp = client.get(f"/api/orders/{order.id}/storage-location/history/")
    assert history_resp.status_code == 200
    history_payload = history_resp.json()
    actions = [event["action"] for event in history_payload["events"]]

    assert history_payload["order_id"] == order.id
    assert "storage_location.assigned" in actions
    assert "storage_location.cleared" in actions


@pytest.mark.django_db
def test_timeline_includes_storage_location_events():
    tenant = Tenant.objects.create(slug="t-loc-timeline", name="T Loc Timeline")
    user = get_user_model().objects.create_user(username="loc-timeline", password="pw")
    client = build_client(tenant=tenant, user=user)

    order = Order.objects.create(tenant=tenant, status="READY")
    sku = f"ORD-{order.id:08d}"

    assign_resp = client.post(
        "/api/orders/storage-locations/assign/",
        data={
            "location_barcode": "LOC-TL1",
            "order_barcode": sku,
            "rack_number": "4",
        },
        format="json",
    )
    assert assign_resp.status_code == 200

    timeline_resp = client.get(f"/api/orders/{order.id}/timeline/")
    assert timeline_resp.status_code == 200
    kinds = [event["kind"] for event in timeline_resp.json()]
    assert "storage_location.assigned" in kinds
