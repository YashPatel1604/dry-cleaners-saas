import json
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from audit.models import AuditEvent
from orders.models import Order
from payments.models import Adjustment


class AdjustmentAuditTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Grab any existing settled order in test DB (if your test factory already seeds these),
        # otherwise you should replace this with your own order factory creation.
        cls.settled_order = Order.objects.filter(
            settled_at__isnull=False).first()

    def setUp(self):
        # If your project uses JWT auth in tests, replace this with your helper
        # (e.g., self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        # or force_authenticate with a user).
        #
        # Leaving as-is because your app’s auth setup isn’t shown here.
        pass

    def test_adjustment_create_emits_audit_event(self):
        if not self.settled_order:
            self.skipTest("No settled order available for test.")

        # DRF router basename likely 'adjustment'
        url = reverse("adjustment-list")
        payload = {
            "order": self.settled_order.id,
            "kind": "WRITE_OFF",
            "direction": "OUT",
            "amount_cents": 1,
            "reference": "adj-test-create-1",
            "note": "audit test",
        }

        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        adj_id = res.data["id"]
        e = AuditEvent.objects.filter(
            action="adjustment.created",
            entity_type="adjustment",
            entity_id=adj_id,
        ).order_by("-created_at").first()

        self.assertIsNotNone(e)
        self.assertIsNone(e.before)
        self.assertEqual(e.after["order_id"], self.settled_order.id)
        self.assertEqual(e.after["kind"], "WRITE_OFF")
        self.assertEqual(e.after["direction"], "OUT")
        self.assertEqual(e.after["status"], "APPLIED")
        self.assertEqual(e.after["amount_cents"], 1)
        self.assertEqual(e.after["reference"], "adj-test-create-1")

    def test_adjustment_void_emits_audit_event(self):
        if not self.settled_order:
            self.skipTest("No settled order available for test.")

        # create adjustment directly
        adj = Adjustment.objects.create(
            tenant=self.settled_order.tenant,
            order=self.settled_order,
            kind=Adjustment.Kind.WRITE_OFF,
            direction=Adjustment.Direction.OUT,
            status=Adjustment.Status.APPLIED,
            amount_cents=1,
            reference="adj-test-void-1",
            note="audit test",
        )

        url = reverse("adjustment-void", args=[adj.id])  # router action name
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        e = AuditEvent.objects.filter(
            action="adjustment.voided",
            entity_type="adjustment",
            entity_id=adj.id,
        ).order_by("-created_at").first()

        self.assertIsNotNone(e)
        self.assertEqual(e.before, {"status": "APPLIED"})
        self.assertEqual(e.after, {"status": "VOIDED"})
        self.assertEqual(e.metadata.get("endpoint"), "adjustments.void")
