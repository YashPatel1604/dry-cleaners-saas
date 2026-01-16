# payments/tests.py
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework.test import APITestCase, APIClient

from tenants.models import Tenant, TenantMembership
from customers.models import Customer

# ✅ CHANGE THIS if your inventory model class is named differently
from inventory.models import InventoryItem

from orders.models import Order, OrderItem

from payments.models import Payment, Adjustment


class PaymentsAndAdjustmentsFlowTests(APITestCase):
    """
    Assumptions:
      - A tenant middleware sets request.tenant based on a header.
      - Routes:
          /api/payments/
          /api/payments/{id}/void/
          /api/payments/summary/
          /api/orders/{id}/receipt/
          /api/adjustments/
          /api/adjustments/{id}/void/
          /api/adjustments/summary/
      - Payments blocked once order.settled_at is set.
      - Adjustments allowed only AFTER settlement.
    """

    def _set_tenant_headers(self, tenant: Tenant):
        # set multiple variants; your middleware only needs one
        self.client.credentials(
            HTTP_X_TENANT=str(tenant.slug),
            HTTP_X_TENANT_SLUG=str(tenant.slug),
            HTTP_X_TENANT_ID=str(tenant.id),
        )

    def _create_order_with_item(self, tenant: Tenant, *, notes="Test order") -> Order:
        customer = Customer.objects.create(
            tenant=tenant,
            name="John Doe",
            phone="714-555-1234",
            email="john@example.com",
        )
        order = Order.objects.create(
            tenant=tenant,
            customer=customer,
            status="RECEIVED",
            notes=notes,
        )

        inv = InventoryItem.objects.create(
            tenant=tenant,
            name="Shirt",
            sku="SHIRT",
            unit_price_cents=399,
        )

        OrderItem.objects.create(
            tenant=tenant,
            order=order,
            item=inv,
            quantity=1,
            unit_price_cents=inv.unit_price_cents,
            line_total_cents=inv.unit_price_cents,
        )
        return order

    def _settle_order_direct(self, order: Order):
        order.settled_at = timezone.now()
        order.save(update_fields=["settled_at"])

    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="u1",
            email="u1@test.com",
            password="pass1234"
        )
        self.client.force_authenticate(self.user)

        self.t1 = Tenant.objects.create(name="T1", slug="t1")
        self.t2 = Tenant.objects.create(name="T2", slug="t2")
        TenantMembership.objects.create(
            tenant=self.t1,
            user=self.user,
            role=TenantMembership.Role.OWNER_ADMIN,
            is_active=True,
        )

        self._set_tenant_headers(self.t1)
        self.order = self._create_order_with_item(
            self.t1, notes="Idempotency test order")

    # ----------------- Payments -----------------

    def test_payment_create_blocks_if_order_settled(self):
        self._settle_order_direct(self.order)

        payload = {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "direction": Payment.Direction.IN,
            "amount_cents": 500,
            "reference": "idem-locked-001",
        }
        resp = self.client.post("/api/payments/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("order", resp.data)

    def test_payment_create_idempotent_reference_returns_same_payment(self):
        payload = {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "direction": Payment.Direction.IN,
            "amount_cents": 500,
            "reference": "idem-test-001",
        }

        resp1 = self.client.post("/api/payments/", payload, format="json")
        self.assertEqual(resp1.status_code, 201)
        pid1 = resp1.data["id"]

        resp2 = self.client.post("/api/payments/", payload, format="json")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data["id"], pid1)
        self.assertEqual(resp2["Idempotent-Replay"], "true")

        self.assertEqual(Payment.objects.filter(
            tenant=self.t1, reference="idem-test-001").count(), 1)

    def test_payment_create_without_reference_creates_new_each_time(self):
        payload = {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "direction": Payment.Direction.IN,
            "amount_cents": 100,
        }

        resp1 = self.client.post("/api/payments/", payload, format="json")
        self.assertEqual(resp1.status_code, 201)

        resp2 = self.client.post("/api/payments/", payload, format="json")
        self.assertEqual(resp2.status_code, 201)

        self.assertNotEqual(resp1.data["id"], resp2.data["id"])

    def test_payment_void_changes_status_and_updates_summary_counts(self):
        resp = self.client.post("/api/payments/", {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "direction": Payment.Direction.IN,
            "amount_cents": 500,
            "reference": "void-test-001",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        pid = resp.data["id"]

        resp_void = self.client.post(
            f"/api/payments/{pid}/void/", {}, format="json")
        self.assertEqual(resp_void.status_code, 200)

        p = Payment.objects.get(id=pid)
        self.assertEqual(p.status, Payment.Status.VOIDED)

        day = timezone.localdate()
        start = (day - timedelta(days=1)).strftime("%Y-%m-%d")
        end = day.strftime("%Y-%m-%d")

        resp_sum = self.client.get(
            f"/api/payments/summary/?start={start}&end={end}&group=day&method_breakdown=1"
        )
        self.assertEqual(resp_sum.status_code, 200)

        totals = resp_sum.data["totals"]
        self.assertEqual(int(totals["count"]), 0)
        self.assertEqual(int(totals["voided_count"]), 1)
        self.assertEqual(int(totals["voided_cents"]), 500)

    def test_payments_summary_group_day_and_method_breakdown(self):
        self.client.post("/api/payments/", {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "direction": Payment.Direction.IN,
            "amount_cents": 500,
            "reference": "sum-a-001",
        }, format="json")
        self.client.post("/api/payments/", {
            "order": self.order.id,
            "method": Payment.Method.CARD,
            "direction": Payment.Direction.IN,
            "amount_cents": 700,
            "reference": "sum-b-001",
        }, format="json")

        day = timezone.localdate()
        start = day.strftime("%Y-%m-%d")
        end = day.strftime("%Y-%m-%d")

        resp = self.client.get(
            f"/api/payments/summary/?start={start}&end={end}&group=day&method_breakdown=1")
        self.assertEqual(resp.status_code, 200)

        totals = resp.data["totals"]
        self.assertEqual(int(totals["count"]), 2)
        self.assertEqual(int(totals["in_cents"]), 1200)
        self.assertEqual(int(totals["out_cents"]), 0)
        self.assertEqual(int(totals["net_cents"]), 1200)

    # ----------------- Adjustments -----------------

    def test_adjustments_blocked_pre_settlement(self):
        payload = {
            "order": self.order.id,
            "kind": getattr(Adjustment.Kind, "REFUND", "REFUND"),
            "direction": Adjustment.Direction.OUT,
            "amount_cents": 50,
            "reference": "adj-pre-001",
        }
        resp = self.client.post("/api/adjustments/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("order", resp.data)

    def test_adjustment_direction_in_only_allowed_for_credit_applied(self):
        self._settle_order_direct(self.order)

        payload = {
            "order": self.order.id,
            "kind": getattr(Adjustment.Kind, "REFUND", "REFUND"),
            "direction": Adjustment.Direction.IN,
            "amount_cents": 50,
            "reference": "adj-in-bad-001",
        }
        resp = self.client.post("/api/adjustments/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(
            "direction" in resp.data or "non_field_errors" in resp.data)

    def test_adjustment_out_cannot_exceed_net_paid(self):
        self.client.post("/api/payments/", {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "direction": Payment.Direction.IN,
            "amount_cents": 100,
            "reference": "pay-net-001",
        }, format="json")

        self._settle_order_direct(self.order)

        resp = self.client.post("/api/adjustments/", {
            "order": self.order.id,
            "kind": getattr(Adjustment.Kind, "REFUND", "REFUND"),
            "direction": Adjustment.Direction.OUT,
            "amount_cents": 999999,
            "reference": "adj-too-big-001",
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("amount_cents", resp.data)

    def test_adjustment_void(self):
        self.client.post("/api/payments/", {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "direction": Payment.Direction.IN,
            "amount_cents": 100,
            "reference": "pay-voidadj-001",
        }, format="json")
        self._settle_order_direct(self.order)

        resp_adj = self.client.post("/api/adjustments/", {
            "order": self.order.id,
            "kind": getattr(Adjustment.Kind, "REFUND", "REFUND"),
            "direction": Adjustment.Direction.OUT,
            "amount_cents": 50,
            "reference": "adj-void-001",
        }, format="json")
        self.assertIn(resp_adj.status_code, (200, 201))

        adj_id = resp_adj.data["id"]
        resp_void = self.client.post(
            f"/api/adjustments/{adj_id}/void/", {}, format="json")
        self.assertEqual(resp_void.status_code, 200)

        adj = Adjustment.objects.get(id=adj_id)
        self.assertEqual(adj.status, Adjustment.Status.VOIDED)

    def test_adjustments_summary_group_day_kind_breakdown(self):
        self.client.post("/api/payments/", {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "direction": Payment.Direction.IN,
            "amount_cents": 100,
            "reference": "pay-sumadj-001",
        }, format="json")
        self._settle_order_direct(self.order)

        self.client.post("/api/adjustments/", {
            "order": self.order.id,
            "kind": getattr(Adjustment.Kind, "REFUND", "REFUND"),
            "direction": Adjustment.Direction.OUT,
            "amount_cents": 50,
            "reference": "adj-sum-001",
        }, format="json")

        day = timezone.localdate()
        start = day.replace(day=1).strftime("%Y-%m-%d")
        end = day.strftime("%Y-%m-%d")

        resp = self.client.get(
            f"/api/adjustments/summary/?start={start}&end={end}&group=day&kind_breakdown=1")
        self.assertEqual(resp.status_code, 200)

        totals = resp.data["totals"]
        self.assertEqual(int(totals["count"]), 1)
        self.assertEqual(int(totals["in_cents"]), 0)
        self.assertEqual(int(totals["out_cents"]), 50)
        self.assertEqual(int(totals["net_cents"]), -50)

    def test_receipt_includes_adjustments_and_net_fields(self):
        self.client.post("/api/payments/", {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "direction": Payment.Direction.IN,
            "amount_cents": 600,
            "reference": "pay-receipt-001",
        }, format="json")
        self._settle_order_direct(self.order)

        self.client.post("/api/adjustments/", {
            "order": self.order.id,
            "kind": getattr(Adjustment.Kind, "REFUND", "REFUND"),
            "direction": Adjustment.Direction.OUT,
            "amount_cents": 50,
            "reference": "adj-receipt-001",
        }, format="json")

        resp = self.client.get(f"/api/orders/{self.order.id}/receipt/")
        self.assertEqual(resp.status_code, 200)

        self.assertIn("payments", resp.data)
        self.assertIn("adjustments", resp.data)
        self.assertIn("adjustments_net_cents", resp.data)
        self.assertIn("net_paid_cents", resp.data)
        self.assertIn("balance_due_cents", resp.data)
        self.assertIn("change_due_cents", resp.data)
