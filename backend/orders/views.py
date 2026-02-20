# orders/views.py
from datetime import timedelta, datetime
from datetime import timezone as dt_timezone
import re


from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.http import HttpResponse
from django.db import IntegrityError
from django.db.models import Q, Count, Sum
from zoneinfo import ZoneInfo

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response

from customers.models import Customer, normalize_phone_us
from payments.models import Payment, Adjustment
from payments.serializers import PaymentSerializer
from audit.models import AuditEvent
from audit.utils import actor_from_request, emit_event
from .services import recalc_order_totals, ReceiptPresenter, render_receipt_pdf, receipt_financials_for_order

from .models import Order, OrderItem, OrderStatusEvent, OrderNote, StorageLocation
from .serializers import (
    OrderSerializer,
    OrderItemSerializer,
    OrderReceiptSerializer,
    OrderStatusEventSerializer,
    OrderCustomerUpdateSerializer,
    OrderNoteSerializer,
)
from tenants.permissions import IsTenantMember
from tenants.utils import parse_limit_offset
from .utils import default_due_at_for_tenant
from .utils import order_sku_for_order, order_id_from_sku

LOCATION_BARCODE_RE = re.compile(r"^LOC-[A-Z0-9][A-Z0-9-]{0,30}$")
ORDER_SCAN_BARCODE_RE = re.compile(r"^ORD-(\d{8})$")
LOCATION_BARCODE_HINT = "Invalid location barcode. Expected format: LOC-<letters/numbers>."
ORDER_BARCODE_HINT = "Invalid order barcode. Expected format: ORD-########."


def parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def normalize_location_barcode(value: str) -> str | None:
    raw = (value or "").strip().upper()
    if not raw:
        return None
    if not LOCATION_BARCODE_RE.match(raw):
        return None
    return raw


def parse_order_id_from_barcode(value: str) -> int | None:
    raw = (value or "").strip()
    if not raw:
        return None
    normalized = raw.upper()
    match = ORDER_SCAN_BARCODE_RE.match(normalized)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None



def compute_net_paid_and_balance(order):
    """
    Returns (net_paid_cents, balance_due_cents) where net_paid includes APPLIED adjustments.
    """
    recalc_order_totals(order)
    order.refresh_from_db(fields=["total_cents", "paid_cents"])

    net_paid = int(order.paid_cents)
    for a in getattr(order, "adjustments").all():
        if a.status != Adjustment.Status.APPLIED:
            continue
        if a.direction == Adjustment.Direction.IN:
            net_paid += int(a.amount_cents)
        else:
            net_paid -= int(a.amount_cents)

    balance_due = max(int(order.total_cents) - net_paid, 0)
    return net_paid, balance_due


def receipt_pdf_url(request, order) -> str:
    path = f"/api/orders/{order.id}/receipt/print/"
    return request.build_absolute_uri(path)


def barcode_svg_url(request, order) -> str:
    path = f"/api/orders/{order.id}/barcode.svg/"
    return request.build_absolute_uri(path)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        # keep list/retrieve fast
        return (
            Order.objects.filter(tenant=self.request.tenant)
            .select_related("customer", "storage_location")
            .prefetch_related("payments", "adjustments")
        )

    def _storage_location_payload(self, order):
        location = getattr(order, "storage_location", None)
        return {
            "order_id": order.id,
            "order_sku": order_sku_for_order(order),
            "location_barcode": getattr(location, "barcode", None),
            "rack_number": getattr(location, "rack_number", None) or None,
            "assigned_at": (
                order.storage_assigned_at.isoformat()
                if order.storage_assigned_at
                else None
            ),
        }

    def _storage_snapshot(self, order):
        location = getattr(order, "storage_location", None)
        return {
            "location_barcode": getattr(location, "barcode", None),
            "rack_number": getattr(location, "rack_number", None) or None,
            "assigned_at": (
                order.storage_assigned_at.isoformat()
                if order.storage_assigned_at
                else None
            ),
        }

    def _emit_storage_audit_event(
        self,
        request,
        *,
        action: str,
        order: Order,
        before: dict,
        after: dict,
        metadata: dict | None = None,
    ):
        emit_event(
            tenant=request.tenant,
            request_id=getattr(request, "request_id", ""),
            actor=actor_from_request(request),
            action=action,
            entity_type="order",
            entity_id=order.id,
            before=before,
            after=after,
            metadata=metadata or {},
        )

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset().order_by("-created_at")
        limit, offset = parse_limit_offset(request, default_limit=None, max_limit=200)
        if limit is not None:
            qs = qs[offset: offset + limit]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        customer = serializer.validated_data.get("customer")
        if customer and not Customer.objects.filter(id=customer.id, tenant=self.request.tenant).exists():
            raise ValidationError(
                {"customer": "Customer does not belong to this tenant."})

        with transaction.atomic():
            due_at = serializer.validated_data.get(
                "due_at") or default_due_at_for_tenant(self.request.tenant)

            order = serializer.save(
                tenant=self.request.tenant,
                received_at=timezone.now(),
                due_at=due_at,
            )

            # timeline starts here
            OrderStatusEvent.objects.create(
                tenant=self.request.tenant,
                order=order,
                from_status=order.status,
                to_status=order.status,
                changed_by=self.request.user if self.request.user.is_authenticated else None,
                note="Order created",
            )

    def perform_update(self, serializer):
        """
        Logs every status change (immutable) and sets lifecycle timestamps on first entry to a state.
        Done under transaction + row lock to avoid race conditions.
        """
        with transaction.atomic():
            locked = Order.objects.select_for_update().get(
                pk=serializer.instance.pk,
                tenant=self.request.tenant,
            )

            old_status = locked.status
            new_status = serializer.validated_data.get("status", old_status)

            order = serializer.save()

            if old_status != new_status:
                OrderStatusEvent.objects.create(
                    tenant=self.request.tenant,
                    order=order,
                    from_status=old_status,
                    to_status=new_status,
                    changed_by=self.request.user if self.request.user.is_authenticated else None,
                )

                now = timezone.now()
                updates = []

                if new_status == "IN_PROGRESS" and order.in_progress_at is None:
                    order.in_progress_at = now
                    updates.append("in_progress_at")
                elif new_status == "READY" and order.ready_at is None:
                    order.ready_at = now
                    updates.append("ready_at")
                elif new_status == "COMPLETED" and order.completed_at is None:
                    order.completed_at = now
                    updates.append("completed_at")
                elif new_status == "CANCELLED" and order.cancelled_at is None:
                    order.cancelled_at = now
                    updates.append("cancelled_at")
                elif new_status == "PICKED_UP" and order.picked_up_at is None:
                    order.picked_up_at = now
                    updates.append("picked_up_at")

                if updates:
                    order.save(update_fields=updates)

    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        """
        GET /api/orders/{id}/receipt/
        Returns an itemized receipt with customer, items, payments, and balance.
        """
        order = (
            Order.objects.filter(tenant=request.tenant, pk=pk)
            .select_related("customer")
            .prefetch_related("items__item", "payments", "adjustments")
            .first()
        )
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        recalc_order_totals(order)
        order.refresh_from_db(fields=[
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
            "settled_at",
            "settled_total_cents",
            "settled_paid_cents",
            "settled_change_cents",
            "settled_balance_due_cents",
        ])

        # ✅ Reprint-stable: once settled, receipts must reflect snapshot fields.
        if order.settled_at is not None:
            order.total_cents = order.settled_total_cents
            order.paid_cents = order.settled_paid_cents

        data = OrderReceiptSerializer(order).data
        data["pdf_url"] = receipt_pdf_url(request, order)
        data["barcode_svg_url"] = barcode_svg_url(request, order)
        return Response(data)

    @action(detail=True, methods=["get"], url_path="receipt/summary")
    def receipt_summary(self, request, pk=None):
        """
        GET /api/orders/{id}/receipt/summary/
        Returns receipt financials without itemized lines.
        """
        order = (
            Order.objects.filter(tenant=request.tenant, pk=pk)
            .select_related("customer")
            .prefetch_related("items__item", "payments", "adjustments")
            .first()
        )
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        recalc_order_totals(order)
        order.refresh_from_db(fields=[
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
            "settled_at",
            "settled_total_cents",
            "settled_paid_cents",
        ])

        if order.settled_at is not None:
            order.total_cents = order.settled_total_cents
            order.paid_cents = order.settled_paid_cents

        data = OrderReceiptSerializer(order).data
        summary_fields = {
            "id",
            "status",
            "due_at",
            "notes",
            "created_at",
            "settled_at",
            "customer",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
            "adjustments_net_cents",
            "net_paid_cents",
            "balance_due_cents",
            "change_due_cents",
        }

        return Response({k: data.get(k) for k in summary_fields})

    @action(detail=True, methods=["get"], url_path="receipt/print")
    def receipt_print(self, request, pk=None):
        order = (
            Order.objects.filter(tenant=request.tenant, pk=pk)
            .select_related("customer")
            .prefetch_related("items__item", "payments", "adjustments")
            .first()
        )
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        # Keep consistent with JSON receipt endpoint
        recalc_order_totals(order)
        order.refresh_from_db(fields=[
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
            "settled_at",
            "settled_total_cents",
            "settled_paid_cents",
        ])

        if order.settled_at is not None:
            order.total_cents = order.settled_total_cents
            order.paid_cents = order.settled_paid_cents

        receipt_dict = ReceiptPresenter(order).build()
        receipt_dict["pdf_url"] = receipt_pdf_url(request, order)
        receipt_dict["barcode_svg_url"] = barcode_svg_url(request, order)
        pdf_bytes = render_receipt_pdf(receipt_dict)

        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="receipt-order-{order.id}.pdf"'
        return resp

    @action(detail=True, methods=["post"], url_path="receipt/email")
    def receipt_email(self, request, pk=None):
        if not getattr(settings, "RECEIPT_EMAIL_ENABLED", False):
            return Response({"detail": "Receipt email not enabled."}, status=501)

        order = (
            Order.objects.filter(tenant=request.tenant, pk=pk)
            .select_related("customer")
            .first()
        )
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        to_email = (request.data.get("to_email") or "").strip()
        if not to_email:
            to_email = getattr(order.customer, "email", "") or ""
        if not to_email:
            raise ValidationError({"to_email": "Recipient email required."})

        pdf_url = receipt_pdf_url(request, order)
        message = f"Your receipt is available here: {pdf_url}"

        send_mail(
            subject=f"Receipt for order #{order.id}",
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[to_email],
            fail_silently=False,
        )

        return Response({"status": "sent"})

    @action(detail=True, methods=["get"], url_path="ticket.pdf")
    def ticket_pdf(self, request, pk=None):
        return self.receipt_print(request, pk=pk)

    @action(detail=True, methods=["get"], url_path="barcode.svg")
    def barcode_svg(self, request, pk=None):
        """
        GET /api/orders/{id}/barcode.svg/
        Returns a Code128 barcode SVG for the order SKU.
        """
        from reportlab.graphics.barcode import createBarcodeDrawing

        order = self.get_object()
        sku = order_sku_for_order(order)
        drawing = createBarcodeDrawing(
            "Code128",
            value=sku,
            barHeight=40,
            barWidth=1.2,
            humanReadable=True,
        )
        svg_bytes = drawing.asString("svg")
        return HttpResponse(svg_bytes, content_type="image/svg+xml")

    @action(detail=False, methods=["post"], url_path="storage-locations/lookup")
    def storage_location_lookup(self, request):
        """
        POST /api/orders/storage-locations/lookup/
        Checks whether a location barcode is already known for this tenant.
        """
        barcode_raw = (request.data.get("barcode") or "").strip()
        if not barcode_raw:
            raise ValidationError({"barcode": "Required."})
        barcode = normalize_location_barcode(barcode_raw)
        if barcode is None:
            raise ValidationError({"barcode": LOCATION_BARCODE_HINT})

        location = StorageLocation.objects.filter(
            tenant=request.tenant, barcode=barcode
        ).first()

        return Response(
            {
                "barcode": barcode,
                "exists": bool(location),
                "rack_number": (
                    getattr(location, "rack_number", None) or None
                    if location
                    else None
                ),
            }
        )

    @action(detail=False, methods=["get"], url_path="storage-locations/status")
    def storage_location_status(self, request):
        """
        GET /api/orders/storage-locations/status/
        Returns all tenant locations with occupancy state and current order SKU.
        Optional query params:
        - q: filter by location barcode or rack number
        - occupied: true/false
        """
        query = (request.query_params.get("q") or "").strip()
        occupied_filter = request.query_params.get("occupied")

        locations_qs = StorageLocation.objects.filter(tenant=request.tenant)
        if query:
            locations_qs = locations_qs.filter(
                Q(barcode__icontains=query) | Q(rack_number__icontains=query)
            )

        locations = list(locations_qs.order_by("rack_number", "barcode", "id"))
        if not locations:
            return Response({"count": 0, "results": []})

        location_ids = [location.id for location in locations]
        assigned_orders = (
            Order.objects.filter(
                tenant=request.tenant,
                storage_location_id__in=location_ids,
            )
            .select_related("storage_location")
        )

        assigned_by_location_id = {}
        for assigned_order in assigned_orders:
            location_id = assigned_order.storage_location_id
            previous = assigned_by_location_id.get(location_id)
            if previous is None:
                assigned_by_location_id[location_id] = assigned_order
                continue

            previous_key = (
                previous.storage_assigned_at or previous.created_at,
                previous.id,
            )
            candidate_key = (
                assigned_order.storage_assigned_at or assigned_order.created_at,
                assigned_order.id,
            )
            if candidate_key > previous_key:
                assigned_by_location_id[location_id] = assigned_order

        only_occupied = None
        if occupied_filter is not None:
            only_occupied = occupied_filter.strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
                "on",
            }

        results = []
        for location in locations:
            assigned_order = assigned_by_location_id.get(location.id)
            is_occupied = assigned_order is not None
            if only_occupied is not None and is_occupied != only_occupied:
                continue

            results.append(
                {
                    "location_barcode": location.barcode,
                    "rack_number": location.rack_number or None,
                    "occupied": is_occupied,
                    "current_order_id": assigned_order.id if assigned_order else None,
                    "current_order_sku": (
                        order_sku_for_order(assigned_order)
                        if assigned_order
                        else None
                    ),
                    "current_order_status": (
                        assigned_order.status if assigned_order else None
                    ),
                    "assigned_at": (
                        assigned_order.storage_assigned_at.isoformat()
                        if assigned_order and assigned_order.storage_assigned_at
                        else None
                    ),
                }
            )

        return Response({"count": len(results), "results": results})

    @action(detail=False, methods=["post"], url_path="storage-locations/assign")
    def storage_location_assign(self, request):
        """
        POST /api/orders/storage-locations/assign/
        Assigns an order to a location barcode (and optional rack number).
        """
        location_barcode_raw = (request.data.get("location_barcode") or "").strip()
        order_barcode = (request.data.get("order_barcode") or "").strip().upper()
        rack_number = (request.data.get("rack_number") or "").strip()
        force_clear = parse_bool(request.data.get("force_clear"), default=False)

        if not location_barcode_raw:
            raise ValidationError({"location_barcode": "Required."})
        location_barcode = normalize_location_barcode(location_barcode_raw)
        if location_barcode is None:
            raise ValidationError({"location_barcode": LOCATION_BARCODE_HINT})
        if not order_barcode:
            raise ValidationError({"order_barcode": "Required."})
        if len(rack_number) > 20:
            raise ValidationError({"rack_number": "Must be 20 characters or fewer."})

        order_id = parse_order_id_from_barcode(order_barcode)
        if order_id is None:
            raise ValidationError({"order_barcode": ORDER_BARCODE_HINT})

        with transaction.atomic():
            order = (
                Order.objects.select_for_update()
                .filter(tenant=request.tenant, pk=order_id)
                .first()
            )
            if not order:
                raise ValidationError(
                    {"order_barcode": "Order not found in this tenant."}
                )
            before_order_snapshot = self._storage_snapshot(order)

            location, created = StorageLocation.objects.select_for_update().get_or_create(
                tenant=request.tenant,
                barcode=location_barcode,
                defaults={"rack_number": rack_number},
            )

            previous_rack_number = location.rack_number or None
            if rack_number and rack_number != (location.rack_number or ""):
                location.rack_number = rack_number
                location.save(update_fields=["rack_number", "updated_at"])
            rack_number_changed = previous_rack_number != (location.rack_number or None)

            occupied_qs = (
                Order.objects.select_for_update()
                .filter(tenant=request.tenant, storage_location=location)
                .exclude(pk=order.id)
                .order_by("created_at", "id")
            )
            occupied_orders = list(occupied_qs)
            occupied_order = occupied_orders[0] if occupied_orders else None

            if occupied_order and not force_clear:
                return Response(
                    {
                        "code": "storage_location_occupied",
                        "detail": "Rack already full.",
                        "location_barcode": location.barcode,
                        "rack_number": location.rack_number or None,
                        "current_order_id": occupied_order.id,
                        "current_order_sku": order_sku_for_order(occupied_order),
                    },
                    status=409,
                )

            cleared_orders = 0
            if occupied_orders and force_clear:
                for occupied in occupied_orders:
                    before_cleared_snapshot = self._storage_snapshot(occupied)
                    occupied.storage_location = None
                    occupied.storage_assigned_at = None
                    occupied.save(
                        update_fields=["storage_location", "storage_assigned_at"]
                    )
                    after_cleared_snapshot = self._storage_snapshot(occupied)
                    self._emit_storage_audit_event(
                        request,
                        action="storage_location.evicted",
                        order=occupied,
                        before=before_cleared_snapshot,
                        after=after_cleared_snapshot,
                        metadata={
                            "reason": "force_clear",
                            "reassigned_to_order_id": order.id,
                            "reassigned_to_order_sku": order_sku_for_order(order),
                            "location_barcode": location.barcode,
                            "rack_number": location.rack_number or None,
                        },
                    )
                    cleared_orders += 1

            order.storage_location = location
            order.storage_assigned_at = timezone.now()
            order.save(update_fields=["storage_location", "storage_assigned_at"])
            after_order_snapshot = self._storage_snapshot(order)
            self._emit_storage_audit_event(
                request,
                action="storage_location.assigned",
                order=order,
                before=before_order_snapshot,
                after=after_order_snapshot,
                metadata={
                    "force_clear": force_clear,
                    "location_created": created,
                    "location_barcode": location.barcode,
                    "rack_number": location.rack_number or None,
                    "order_barcode": order_barcode,
                    "rack_number_changed": rack_number_changed,
                    "rack_number_before": previous_rack_number,
                    "rack_number_after": location.rack_number or None,
                },
            )

        payload = self._storage_location_payload(order)
        payload["location_created"] = created
        payload["cleared_orders"] = cleared_orders
        return Response(payload, status=200)

    @action(detail=True, methods=["get"], url_path="storage-location")
    def storage_location(self, request, pk=None):
        """
        GET /api/orders/{id}/storage-location/
        Returns current location assignment for an order.
        """
        order = self.get_object()
        return Response(self._storage_location_payload(order))

    @action(detail=True, methods=["get"], url_path="storage-location/history")
    def storage_location_history(self, request, pk=None):
        """
        GET /api/orders/{id}/storage-location/history/
        Returns assignment/clear history with actor + before/after snapshots.
        """
        order = self.get_object()
        events_qs = (
            AuditEvent.objects.filter(
                tenant=request.tenant,
                entity_type="order",
                entity_id=str(order.id),
                action__startswith="storage_location.",
            )
            .order_by("-created_at")
        )

        limit, offset = parse_limit_offset(request, default_limit=50, max_limit=200)
        if limit is not None:
            events_qs = events_qs[offset: offset + limit]

        events = [
            {
                "id": str(event.id),
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "action": event.action,
                "actor_type": event.actor_type,
                "actor_id": event.actor_id,
                "actor_label": event.actor_label,
                "request_id": event.request_id,
                "before": event.before or {},
                "after": event.after or {},
                "metadata": event.metadata or {},
            }
            for event in events_qs
        ]
        return Response({"order_id": order.id, "count": len(events), "events": events})

    @action(detail=True, methods=["post"], url_path="storage-location/clear")
    def clear_storage_location(self, request, pk=None):
        """
        POST /api/orders/{id}/storage-location/clear/
        Clears current location assignment.
        """
        with transaction.atomic():
            order = (
                Order.objects.select_for_update()
                .filter(tenant=request.tenant, pk=pk)
                .first()
            )
            if not order:
                raise ValidationError({"order": "Order not found in this tenant."})

            before_snapshot = self._storage_snapshot(order)
            order.storage_location = None
            order.storage_assigned_at = None
            order.save(update_fields=["storage_location", "storage_assigned_at"])
            after_snapshot = self._storage_snapshot(order)
            if (
                before_snapshot["location_barcode"] is not None
                or before_snapshot["assigned_at"] is not None
            ):
                self._emit_storage_audit_event(
                    request,
                    action="storage_location.cleared",
                    order=order,
                    before=before_snapshot,
                    after=after_snapshot,
                    metadata={"reason": "manual_clear"},
                )

        return Response(self._storage_location_payload(order))

    @action(detail=True, methods=["post"], url_path="pickup-payment")
    def pickup_payment(self, request, pk=None):
        """
        POST /api/orders/{id}/pickup-payment/
        Records a payment at pickup time.
        - Allows overpay ONLY for CASH, and auto-creates an OUT payment for change.
        - Idempotent by reference if provided (tenant-scoped).
        Body:
        {
        "amount_cents": 1234,
        "method": "CASH",
        "reference": "pickup-001",
        "note": "..."
        }
        """
        order = (
            Order.objects.filter(tenant=request.tenant, pk=pk)
            .select_related("customer")
            .prefetch_related("adjustments", "payments", "items__item")
            .first()
        )
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        # 🔒 settlement lock
        if getattr(order, "settled_at", None) is not None:
            raise ValidationError(
                {"order": "Order is settled and cannot accept payments."})

        # policy: only allow pickup payments when order is READY/COMPLETED
        if order.status not in ("READY", "COMPLETED"):
            raise ValidationError(
                {"order": "Pickup payments only allowed for READY/COMPLETED orders."})

        # validate fields
        try:
            amount_cents = int(request.data.get("amount_cents"))
        except Exception:
            raise ValidationError({"amount_cents": "Required integer."})

        if amount_cents <= 0:
            raise ValidationError({"amount_cents": "Must be > 0."})

        method = request.data.get("method")
        if method not in Payment.Method.values:
            raise ValidationError(
                {"method": f"Invalid. Allowed: {list(Payment.Method.values)}"})

        reference = (request.data.get("reference") or "").strip()
        note = request.data.get("note") or ""

        # compute current balance due (considers APPLIED adjustments)
        _, balance_due = compute_net_paid_and_balance(order)

        # Non-cash cannot overpay
        if method != Payment.Method.CASH and amount_cents > balance_due:
            raise ValidationError(
                {"amount_cents": f"Payment exceeds balance due ({balance_due})."})

        # If cash overpay, compute change
        change_cents = 0
        if method == Payment.Method.CASH:
            change_cents = max(amount_cents - balance_due, 0)

            # IMPORTANT: if we're going to create a change OUT and client retries,
            # we need deterministic idempotency for BOTH records.
            if change_cents > 0 and not reference:
                raise ValidationError(
                    {"reference": "Required when CASH payment results in change."})

        change_ref = f"{reference}-change" if reference else ""

        # ✅ Idempotency (single source of truth):
        # If reference exists, fetch IN + optional OUT(change) and return them.
        if reference:
            existing_in = Payment.objects.filter(
                tenant=request.tenant,
                order_id=order.id,
                reference=reference,
                direction=Payment.Direction.IN,
            ).first()

            if existing_in:
                existing_change = None
                if method == Payment.Method.CASH:
                    existing_change = Payment.objects.filter(
                        tenant=request.tenant,
                        order_id=order.id,
                        reference=change_ref,
                        direction=Payment.Direction.OUT,
                    ).first()

                # always return current order snapshot
                recalc_order_totals(order)
                order.refresh_from_db(fields=["paid_cents", "total_cents"])

                resp = Response({
                    "payment": PaymentSerializer(existing_in).data,
                    "change_payment": PaymentSerializer(existing_change).data if existing_change else None,
                    "order": OrderSerializer(order).data,
                }, status=200)
                resp["Idempotent-Replay"] = "true"
                return resp

        # create in+out atomically so we never need "healing math"
        try:
            with transaction.atomic():
                # lock order row to prevent races with other payment attempts
                Order.objects.select_for_update().get(pk=order.pk, tenant=request.tenant)

                # recompute inside lock (balance could have changed since read)
                _, locked_balance_due = compute_net_paid_and_balance(order)

                if method != Payment.Method.CASH and amount_cents > locked_balance_due:
                    raise ValidationError(
                        {"amount_cents": f"Payment exceeds balance due ({locked_balance_due})."})

                locked_change_cents = 0
                if method == Payment.Method.CASH:
                    locked_change_cents = max(
                        amount_cents - locked_balance_due, 0)
                    if locked_change_cents > 0 and not reference:
                        raise ValidationError(
                            {"reference": "Required when CASH payment results in change."})

                locked_change_ref = f"{reference}-change" if reference else ""

                payment_in = Payment.objects.create(
                    tenant=request.tenant,
                    order=order,
                    method=method,
                    status=Payment.Status.CAPTURED,
                    direction=Payment.Direction.IN,
                    amount_cents=amount_cents,
                    reference=reference,
                    note=note,
                )

                payment_out = None
                if method == Payment.Method.CASH and locked_change_cents > 0:
                    payment_out = Payment.objects.create(
                        tenant=request.tenant,
                        order=order,
                        method=Payment.Method.CASH,
                        status=Payment.Status.CAPTURED,
                        direction=Payment.Direction.OUT,
                        amount_cents=locked_change_cents,
                        reference=locked_change_ref,
                        note="Auto change-out",
                    )

        except IntegrityError:
            # If you have a UNIQUE(tenant, reference) on Payment, this catches races.
            # Return the idempotent replay result.
            if reference:
                existing_in = Payment.objects.filter(
                    tenant=request.tenant,
                    order_id=order.id,
                    reference=reference,
                    direction=Payment.Direction.IN,
                ).first()
                existing_change = Payment.objects.filter(
                    tenant=request.tenant,
                    order_id=order.id,
                    reference=change_ref,
                    direction=Payment.Direction.OUT,
                ).first() if change_ref else None

                recalc_order_totals(order)
                order.refresh_from_db(fields=["paid_cents", "total_cents"])

                resp = Response({
                    "payment": PaymentSerializer(existing_in).data if existing_in else None,
                    "change_payment": PaymentSerializer(existing_change).data if existing_change else None,
                    "order": OrderSerializer(order).data,
                }, status=200)
                resp["Idempotent-Replay"] = "true"
                return resp
            raise

        # Recalc and return updated order
        recalc_order_totals(order)
        order.refresh_from_db(fields=["paid_cents", "total_cents"])

        return Response({
            "payment": PaymentSerializer(payment_in).data,
            "change_payment": PaymentSerializer(payment_out).data if payment_out else None,
            "order": OrderSerializer(order).data,
        }, status=201)

    @action(detail=True, methods=["post"], url_path="cash-out")
    def cash_out(self, request, pk=None):
        """
        POST /api/orders/{id}/cash-out/
        Records a CAPTURED OUT payment (refund/change/cash payout).
        Idempotent by reference (tenant-scoped).
        Body:
        {
        "amount_cents": 50,
        "method": "CASH",
        "reference": "out-001",
        "note": "Refund / change / payout"
        }
        """
        order = (
            Order.objects.filter(tenant=request.tenant, pk=pk)
            .select_related("customer")
            .prefetch_related("payments", "adjustments", "items__item")
            .first()
        )
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        # 🔒 block after settlement (Option A lock)
        if order.settled_at is not None:
            raise ValidationError(
                {"order": "Order is settled and cannot accept cash-out."})

        # validate amount
        try:
            amount_cents = int(request.data.get("amount_cents"))
        except Exception:
            raise ValidationError({"amount_cents": "Required integer."})
        if amount_cents <= 0:
            raise ValidationError({"amount_cents": "Must be > 0."})

        # validate method
        method = request.data.get("method")
        if method not in Payment.Method.values:
            raise ValidationError(
                {"method": f"Invalid. Allowed: {list(Payment.Method.values)}"})

        reference = (request.data.get("reference") or "").strip()
        note = request.data.get("note") or ""

        # ✅ idempotent by reference
        if reference:
            existing = Payment.objects.filter(
                tenant=request.tenant, reference=reference).first()
            if existing:
                if existing.order_id != order.id:
                    raise ValidationError(
                        {"reference": "Reference already used for a different order."})
                if existing.direction != Payment.Direction.OUT:
                    raise ValidationError(
                        {"reference": "Reference exists but is not an OUT payment."})
                resp = Response(PaymentSerializer(existing).data, status=200)
                resp["Idempotent-Replay"] = "true"
                return resp

        with transaction.atomic():
            payment_out = Payment.objects.create(
                tenant=request.tenant,
                order=order,
                method=method,
                status=Payment.Status.CAPTURED,
                direction=Payment.Direction.OUT,
                amount_cents=amount_cents,
                reference=reference,
                note=note or "Cash out",
            )

        recalc_order_totals(order)
        order.refresh_from_db(fields=["paid_cents", "total_cents"])

        return Response(
            {"payment_out": PaymentSerializer(
                payment_out).data, "order": OrderSerializer(order).data},
            status=201
        )

    @action(detail=True, methods=["post"], url_path="pickup")
    def pickup(self, request, pk=None):
        """
        POST /api/orders/{id}/pickup/
        Confirms order pickup. Default behavior: requires paid-in-full.
        Optional payload: {"allow_balance_due": true}
        """
        tenant_requires_full = bool(
            getattr(request.tenant, "require_paid_in_full_at_pickup", True))

        # If tenant requires full payment, allow_balance_due defaults to False
        # If tenant does NOT require full payment, allow_balance_due defaults to True
        default_allow = (not tenant_requires_full)
        allow_balance_due = parse_bool(
            request.data.get("allow_balance_due"), default=default_allow
        )
        clear_location = parse_bool(request.data.get("clear_location"), default=False)

        order = (
            Order.objects.filter(tenant=request.tenant, pk=pk)
            .select_related("customer")
            .prefetch_related("payments", "adjustments", "items__item")
            .first()
        )
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

            # 🔒 settlement lock (pickup is not allowed after settlement)
        if order.settled_at is not None:
            raise ValidationError(
                {"order": "Order is settled and cannot be picked up."})

            # ✅ idempotency: if already picked up, return current state
        if order.status == "PICKED_UP":
            if clear_location and (
                order.storage_location_id is not None or order.storage_assigned_at is not None
            ):
                with transaction.atomic():
                    locked = Order.objects.select_for_update().get(
                        pk=order.pk, tenant=request.tenant
                    )
                    before_snapshot = self._storage_snapshot(locked)
                    locked.storage_location = None
                    locked.storage_assigned_at = None
                    locked.save(update_fields=["storage_location", "storage_assigned_at"])
                    after_snapshot = self._storage_snapshot(locked)
                    self._emit_storage_audit_event(
                        request,
                        action="storage_location.cleared",
                        order=locked,
                        before=before_snapshot,
                        after=after_snapshot,
                        metadata={"reason": "pickup_clear"},
                    )
                order.refresh_from_db()
            resp = Response(OrderSerializer(order).data, status=200)
            resp["Idempotent-Replay"] = "true"
            return resp

        if order.status not in ("READY", "COMPLETED"):
            raise ValidationError(
                {"order": "Order must be READY/COMPLETED before pickup."})

        recalc_order_totals(order)
        order.refresh_from_db(fields=["total_cents", "paid_cents"])

        net_paid = int(order.paid_cents)
        for a in getattr(order, "adjustments").all():
            if a.status != Adjustment.Status.APPLIED:
                continue
            if a.direction == Adjustment.Direction.IN:
                net_paid += int(a.amount_cents)
            else:
                net_paid -= int(a.amount_cents)

        balance_due = max(int(order.total_cents) - net_paid, 0)

        if balance_due > 0 and not allow_balance_due:
            raise ValidationError(
                {"order": "Balance due. Collect payment or pass allow_balance_due=true."})

        with transaction.atomic():
            locked = Order.objects.select_for_update().get(
                pk=order.pk, tenant=request.tenant)

            if locked.status == "PICKED_UP":
                return Response(OrderSerializer(locked).data)

            old_status = locked.status
            locked.status = "PICKED_UP"

            now = timezone.now()
            if locked.picked_up_at is None:
                locked.picked_up_at = now

            update_fields = ["status", "picked_up_at"]
            before_snapshot = self._storage_snapshot(locked)
            if clear_location:
                locked.storage_location = None
                locked.storage_assigned_at = None
                update_fields.extend(["storage_location", "storage_assigned_at"])

            locked.save(update_fields=update_fields)
            after_snapshot = self._storage_snapshot(locked)
            if (
                clear_location
                and (
                    before_snapshot["location_barcode"] is not None
                    or before_snapshot["assigned_at"] is not None
                )
            ):
                self._emit_storage_audit_event(
                    request,
                    action="storage_location.cleared",
                    order=locked,
                    before=before_snapshot,
                    after=after_snapshot,
                    metadata={"reason": "pickup_clear"},
                )

            OrderStatusEvent.objects.create(
                tenant=request.tenant,
                order=locked,
                from_status=old_status,
                to_status="PICKED_UP",
                changed_by=request.user if request.user.is_authenticated else None,
                note="Picked up",
            )

        order.refresh_from_db()
        return Response(OrderSerializer(order).data)

    @action(detail=False, methods=["get"], url_path="ready-unpaid")
    def ready_unpaid(self, request):
        """
        GET /api/orders/ready-unpaid/
        Orders that are READY/COMPLETED but still have balance due (considering adjustments).
        """
        qs = (
            Order.objects.filter(tenant=request.tenant,
                                 status__in=["READY", "COMPLETED"])
            .select_related("customer")
            .prefetch_related("adjustments")
            .order_by("-created_at")[:200]
        )

        results = []
        for o in qs:
            net_paid = int(o.paid_cents)
            for a in getattr(o, "adjustments").all():
                if a.status != Adjustment.Status.APPLIED:
                    continue
                if a.direction == Adjustment.Direction.IN:
                    net_paid += int(a.amount_cents)
                else:
                    net_paid -= int(a.amount_cents)

            balance_due = max(int(o.total_cents) - net_paid, 0)
            if balance_due > 0:
                data = OrderSerializer(o).data
                data["balance_due_cents"] = balance_due
                data["net_paid_cents"] = net_paid
                results.append(data)

        return Response(results)

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        """
        POST /api/orders/{id}/settle/
        Locks the order financially:
        - requires COMPLETED
        - requires paid >= total (no balance due)
        - sets settled_at + snapshot fields exactly once
        """
        order = (
            Order.objects.filter(tenant=request.tenant, pk=pk)
            .select_related("customer")
            .prefetch_related("items__item", "payments", "adjustments")
            .first()
        )
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        if order.status != "COMPLETED":
            raise ValidationError(
                {"order": "Order must be COMPLETED before settlement."})

        if order.settled_at is not None:
            data = OrderReceiptSerializer(order).data
            resp = Response(data)
            resp["Idempotent-Replay"] = "true"
            return resp

        recalc_order_totals(order)
        order.refresh_from_db(fields=["total_cents", "paid_cents"])

        if int(order.paid_cents) < int(order.total_cents):
            return Response({"order": "Order has balance due and cannot be settled."}, status=400)

        settled_total = int(order.total_cents)
        settled_paid = int(order.paid_cents)
        settled_change = max(settled_paid - settled_total, 0)
        settled_balance_due = max(settled_total - settled_paid, 0)

        with transaction.atomic():
            locked = Order.objects.select_for_update().get(pk=order.pk)

            if locked.settled_at is not None:
                data = OrderReceiptSerializer(locked).data
                resp = Response(data)
                resp["Idempotent-Replay"] = "true"
                return resp

            locked.settled_at = timezone.now()
            locked.settled_total_cents = settled_total
            locked.settled_paid_cents = settled_paid
            locked.settled_change_cents = settled_change
            locked.settled_balance_due_cents = settled_balance_due

            locked.save(update_fields=[
                "settled_at",
                "settled_total_cents",
                "settled_paid_cents",
                "settled_change_cents",
                "settled_balance_due_cents",
            ])

        order.refresh_from_db()
        data = OrderReceiptSerializer(order).data
        return Response(data)

    @action(detail=True, methods=["get"], url_path="status-events")
    def status_events(self, request, pk=None):
        """
        GET /api/orders/{id}/status-events/
        Returns the immutable timeline of status transitions.
        """
        order = Order.objects.filter(tenant=request.tenant, pk=pk).first()
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        qs = OrderStatusEvent.objects.filter(
            tenant=request.tenant, order=order).order_by("created_at")
        return Response(OrderStatusEventSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="mark_ready")
    def mark_ready(self, request, pk=None):
        order = self.get_object()
        if order.status == "READY":
            return Response(OrderSerializer(order).data)

        serializer = OrderSerializer(
            order,
            data={"status": "READY"},
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="set_customer_by_phone")
    def set_customer_by_phone(self, request, pk=None):
        raw_phone = (request.data.get("phone") or "").strip()
        if not raw_phone:
            raise ValidationError({"phone": "Required"})

        phone_e164 = normalize_phone_us(raw_phone)
        if not phone_e164:
            raise ValidationError(
                {"phone": "Invalid/unsupported phone format"})

        order = Order.objects.filter(tenant=request.tenant, pk=pk).first()
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        customer = Customer.objects.filter(
            tenant=request.tenant, phone_e164=phone_e164).first()

        if not customer:
            name = (request.data.get("name") or "").strip()
            if not name:
                raise ValidationError(
                    {"name": "Name is required to create a new customer."})

            customer = Customer.objects.create(
                tenant=request.tenant,
                name=name,
                phone=raw_phone,
                email=(request.data.get("email") or "").strip(),
                notes=(request.data.get("notes") or "").strip(),
            )

        order.customer = customer
        order.save(update_fields=["customer"])

        return Response(OrderSerializer(order).data)

    @action(detail=False, methods=["post"], url_path="dropoff")
    def dropoff(self, request):
        """
        POST /api/orders/dropoff/
        Creates an order and optionally records an initial payment (deposit/full).
        Idempotency supported via initial_payment.reference (tenant-scoped).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer_id = serializer.validated_data["customer"].id
        if not Customer.objects.filter(id=customer_id, tenant=request.tenant).exists():
            raise ValidationError(
                {"customer": "Customer does not belong to this tenant."})

        if serializer.validated_data.get("status") == "CANCELLED":
            raise ValidationError(
                {"status": "Cannot create a cancelled order at dropoff."})

        initial_payment = request.data.get("initial_payment")

        with transaction.atomic():
            due_at = serializer.validated_data.get(
                "due_at") or default_due_at_for_tenant(request.tenant)

            order = serializer.save(
                tenant=request.tenant,
                received_at=timezone.now(),
                due_at=due_at,
            )

            OrderStatusEvent.objects.create(
                tenant=request.tenant,
                order=order,
                from_status=order.status,
                to_status=order.status,
                changed_by=request.user if request.user.is_authenticated else None,
                note="Order created",
            )

            if getattr(order, "settled_at", None) is not None:
                raise ValidationError(
                    {"order": "Order is settled and cannot accept payments."})

            payment_obj = None
            if initial_payment:
                try:
                    amount_cents = int(initial_payment.get("amount_cents", 0))
                except Exception:
                    raise ValidationError(
                        {"initial_payment.amount_cents": "Must be integer."})

                method = initial_payment.get("method")
                if amount_cents <= 0:
                    raise ValidationError(
                        {"initial_payment.amount_cents": "Must be > 0."})
                if method not in Payment.Method.values:
                    raise ValidationError(
                        {"initial_payment.method": f"Invalid. Allowed: {list(Payment.Method.values)}"})

                reference = (initial_payment.get("reference") or "").strip()

                # ✅ idempotent by tenant+reference
                if reference:
                    existing = Payment.objects.filter(
                        tenant=request.tenant, reference=reference).first()
                    if existing and existing.order_id != order.id:
                        raise ValidationError(
                            {"initial_payment.reference": "Reference already used for a different order."})
                    payment_obj = existing

                if payment_obj is None:
                    payment_obj = Payment.objects.create(
                        tenant=request.tenant,
                        order=order,
                        method=method,
                        status=Payment.Status.CAPTURED,
                        direction=Payment.Direction.IN,
                        amount_cents=amount_cents,
                        reference=reference,
                        note=(initial_payment.get("note") or ""),
                    )

                recalc_order_totals(order)
                order.refresh_from_db(
                    fields=["subtotal_cents", "tax_cents", "total_cents", "paid_cents"])

        order.refresh_from_db()
        payload = OrderSerializer(order).data
        if payment_obj:
            payload["initial_payment"] = PaymentSerializer(payment_obj).data

        return Response(payload, status=201)

    @action(detail=True, methods=["get"], url_path="audit")
    def audit(self, request, pk=None):
        """
        GET /api/orders/{id}/audit/
        Raw audit feed (developer/compliance oriented). Includes:
        - order audit events
        - payment audit events for payments on this order
        - adjustment audit events for adjustments on this order
        """
        order = self.get_object()  # already tenant-scoped via get_queryset()

        payment_ids = list(
            Payment.objects.filter(
                tenant=request.tenant, order_id=order.id
            ).values_list("id", flat=True)
        )
        adjustment_ids = list(
            Adjustment.objects.filter(
                tenant=request.tenant, order_id=order.id
            ).values_list("id", flat=True)
        )

        qs = (
            AuditEvent.objects.filter(tenant=request.tenant)
            .filter(
                Q(entity_type="order", entity_id=str(order.id))
                | Q(entity_type="payment", entity_id__in=[str(i) for i in payment_ids])
                | Q(entity_type="adjustment", entity_id__in=[str(i) for i in adjustment_ids])
            )
            .order_by("created_at")
        )

        data = [
            {
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "actor_type": e.actor_type,
                "actor_id": e.actor_id,
                "actor_label": e.actor_label,
                "request_id": e.request_id,
                "before": e.before,
                "after": e.after,
                "metadata": e.metadata,
            }
            for e in qs
        ]

        return Response({"order_id": order.id, "count": len(data), "events": data})

    @action(detail=True, methods=["get", "post"], url_path="notes")
    def notes(self, request, pk=None):
        order = self.get_object()

        if request.method.lower() == "post":
            serializer = OrderNoteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            note_text = serializer.validated_data["note"].strip()
            if not note_text:
                raise ValidationError({"note": "Note cannot be empty."})
            note = OrderNote.objects.create(
                tenant=request.tenant,
                order=order,
                author=request.user if request.user.is_authenticated else None,
                note=note_text,
            )
            return Response(OrderNoteSerializer(note).data, status=201)

        qs = (
            OrderNote.objects.filter(tenant=request.tenant, order=order)
            .select_related("author")
            .order_by("-created_at")
        )
        limit, offset = parse_limit_offset(request, default_limit=50, max_limit=200)
        if limit is not None:
            qs = qs[offset: offset + limit]
        return Response(OrderNoteSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline(self, request, pk=None):
        """
        GET /api/orders/{id}/timeline/
        Operator-friendly merged timeline:
        - order.created (derived)
        - status.change (OrderStatusEvent)
        - payment.* (Payment)
        - adjustment.* (Adjustment)
        - settlement.snapshot (derived from Order.settled_* fields)
        """
        order = self.get_object()  # tenant-safe

        def actor_from_user(user):
            if user:
                return {
                    "type": "USER",
                    "id": str(user.id),
                    "label": getattr(user, "username", "") or str(user),
                }
            return {"type": "SYSTEM", "id": "", "label": "system"}

        def amount_obj(cents: int):
            return {"currency": "USD", "cents": int(cents)}

        def event_type_priority(kind: str) -> int:
            priority = {
                "order.created": 10,
                "status.change": 20,
                "storage_location.assigned": 22,
                "storage_location.cleared": 23,
                "storage_location.evicted": 24,
                "note.added": 25,
                "payment.created": 30,
                "payment.voided": 31,
                "adjustment.applied": 40,
                "adjustment.voided": 41,
                "settlement.snapshot": 50,
            }
            return priority.get(kind, 99)

        def normalize_event(e: dict) -> dict:
            # Preserve existing keys while adding explicit aliases for stability.
            e["event_type"] = e.get("kind")
            e["created_at"] = e.get("at")
            return e

        events = []

        # 1) Order created (derived)
        events.append(normalize_event({
            "id": f"order:{order.id}",
            "at": order.created_at,
            "kind": "order.created",
            "title": "Order created",
            "summary": f"Order #{order.id} created",
            "actor": {"type": "SYSTEM", "id": "", "label": "system"},
            "amount": None,
            "refs": {"order_id": order.id, "status_event_id": None, "payment_id": None, "adjustment_id": None},
            "meta": {},
        }))

        # 2) Status events
        status_events = (
            OrderStatusEvent.objects
            .filter(tenant=request.tenant, order=order)
            .select_related("changed_by")
            .order_by("created_at")
        )
        for se in status_events:
            events.append(normalize_event({
                "id": f"status:{se.id}",
                "at": se.created_at,
                "kind": "status.change",
                "title": "Status changed",
                "summary": f"{se.from_status} → {se.to_status}",
                "actor": actor_from_user(se.changed_by),
                "amount": None,
                "refs": {"order_id": order.id, "status_event_id": se.id, "payment_id": None, "adjustment_id": None},
                "meta": {"from_status": se.from_status, "to_status": se.to_status, "note": se.note or ""},
            }))

        # 3) Notes
        notes = (
            OrderNote.objects
            .filter(tenant=request.tenant, order=order)
            .select_related("author")
            .order_by("created_at")
        )
        for n in notes:
            events.append(normalize_event({
                "id": f"note:{n.id}",
                "at": n.created_at,
                "kind": "note.added",
                "title": "Note added",
                "summary": (n.note or "")[:140],
                "actor": actor_from_user(n.author),
                "amount": None,
                "refs": {"order_id": order.id, "status_event_id": None, "payment_id": None, "adjustment_id": None},
                "meta": {"note": n.note or ""},
            }))

        # 4) Storage assignment/clear events
        storage_events = (
            AuditEvent.objects
            .filter(
                tenant=request.tenant,
                entity_type="order",
                entity_id=str(order.id),
                action__startswith="storage_location.",
            )
            .order_by("created_at")
        )
        for event in storage_events:
            meta = event.metadata or {}
            before = event.before or {}
            after = event.after or {}

            if event.action == "storage_location.assigned":
                title = "Storage assigned"
                location_barcode = after.get("location_barcode") or meta.get("location_barcode")
                rack_number = after.get("rack_number") or meta.get("rack_number")
                summary = location_barcode or "Location assigned"
                if rack_number:
                    summary = f"{summary} (Rack {rack_number})"
            elif event.action == "storage_location.cleared":
                title = "Storage cleared"
                cleared_location = (
                    before.get("location_barcode")
                    or meta.get("location_barcode")
                    or "Location"
                )
                summary = f"{cleared_location} cleared"
            else:
                title = "Storage replaced"
                replaced_sku = meta.get("reassigned_to_order_sku")
                summary = (
                    f"Cleared for {replaced_sku}"
                    if replaced_sku
                    else "Cleared for reassignment"
                )

            events.append(normalize_event({
                "id": f"storage:{event.id}",
                "at": event.created_at,
                "kind": event.action,
                "title": title,
                "summary": summary,
                "actor": {
                    "type": event.actor_type,
                    "id": event.actor_id,
                    "label": event.actor_label or "system",
                },
                "amount": None,
                "refs": {
                    "order_id": order.id,
                    "status_event_id": None,
                    "payment_id": None,
                    "adjustment_id": None,
                },
                "meta": {
                    "before": before,
                    "after": after,
                    **meta,
                },
            }))

        # 5) Payments
        payments = (
            Payment.objects
            .filter(tenant=request.tenant, order=order)
            .order_by("created_at")
        )
        for p in payments:
            signed = int(
                p.amount_cents) if p.direction == Payment.Direction.IN else -int(p.amount_cents)
            kind = "payment.created" if p.status == Payment.Status.CAPTURED else "payment.voided"
            title = "Payment received" if kind == "payment.created" else "Payment voided"

            events.append(normalize_event({
                "id": f"payment:{p.id}",
                "at": p.created_at,
                "kind": kind,
                "title": title,
                "summary": f"{p.method} {'+' if signed >= 0 else ''}{signed/100:.2f}",
                "actor": {"type": "SYSTEM", "id": "", "label": "system"},
                "amount": amount_obj(signed),
                "refs": {"order_id": order.id, "status_event_id": None, "payment_id": p.id, "adjustment_id": None},
                "meta": {
                    "method": p.method,
                    "status": p.status,
                    "direction": p.direction,
                    "reference": p.reference,
                    "note": p.note or "",
                },
            }))

        # 6) Adjustments
        adjustments = (
            Adjustment.objects
            .filter(tenant=request.tenant, order=order)
            .order_by("created_at")
        )
        for a in adjustments:
            signed = int(
                a.amount_cents) if a.direction == Adjustment.Direction.IN else -int(a.amount_cents)
            kind = "adjustment.applied" if a.status == Adjustment.Status.APPLIED else "adjustment.voided"
            title = "Adjustment applied" if kind == "adjustment.applied" else "Adjustment voided"

            events.append(normalize_event({
                "id": f"adjustment:{a.id}",
                "at": a.created_at,
                "kind": kind,
                "title": title,
                "summary": f"{a.kind} {'+' if signed >= 0 else ''}{signed/100:.2f}",
                "actor": {"type": "SYSTEM", "id": "", "label": "system"},
                "amount": amount_obj(signed),
                "refs": {"order_id": order.id, "status_event_id": None, "payment_id": None, "adjustment_id": a.id},
                "meta": {
                    "kind": a.kind,
                    "status": a.status,
                    "direction": a.direction,
                    "reference": a.reference,
                    "note": a.note or "",
                },
            }))

        # 7) Settlement snapshot (derived)
        if order.settled_at is not None:
            events.append(normalize_event({
                "id": f"order:{order.id}:settlement",
                "at": order.settled_at,
                "kind": "settlement.snapshot",
                "title": "Settlement snapshot",
                "summary": "Totals locked for accounting",
                "actor": {"type": "SYSTEM", "id": "", "label": "system"},
                "amount": None,
                "refs": {"order_id": order.id, "status_event_id": None, "payment_id": None, "adjustment_id": None},
                "meta": {
                    "settled_total_cents": order.settled_total_cents,
                    "settled_paid_cents": order.settled_paid_cents,
                    "settled_change_cents": order.settled_change_cents,
                    "settled_balance_due_cents": order.settled_balance_due_cents,
                },
            }))

        events.sort(key=lambda e: (
            e.get("at"),
            event_type_priority(e.get("kind")),
            e.get("id"),
        ))
        return Response(events)

    @action(detail=True, methods=["get"], url_path="labels")
    def labels(self, request, pk=None):
        """
        GET /api/orders/{id}/labels/
        Returns label payloads (one per piece) for printing later.
        Invoice number = order.id.
        """
        # ✅ 404 if not in this tenant (because get_queryset is tenant-scoped)
        order = self.get_object()

        # pull related data efficiently
        order = (
            Order.objects.filter(tenant=request.tenant, pk=order.pk)
            .select_related("customer")
            .prefetch_related("items__item")
            .get()
        )

        customer_name = getattr(order.customer, "name", "") or ""

        labels = []
        seq = 1

        items = sorted(list(order.items.all()),
                       key=lambda oi: (oi.id, oi.item_id))
        for oi in items:
            item_name = ""
            if getattr(oi, "item", None) is not None:
                item_name = getattr(oi.item, "name", "") or str(oi.item)

            qty = int(getattr(oi, "quantity", 1) or 1)
            qty = max(qty, 1)

            for _ in range(qty):
                label_code = f"ORD-{order.id}-{seq:03d}"
                labels.append({
                    "order_id": order.id,
                    "label_code": label_code,
                    "sequence": seq,
                    "customer_name": customer_name,
                    "due_at": order.due_at.isoformat() if order.due_at else None,
                    "item_name": item_name,
                    "order_item_id": oi.id,
                })
                seq += 1

        return Response({"order_id": order.id, "count": len(labels), "labels": labels})

    @action(detail=False, methods=["get"], url_path="queue")
    def queue(self, request):
        """
        /api/orders/queue/?status=READY
        /api/orders/queue/?status=READY&ready_unpaid=1
        /api/orders/queue/?status=IN_PROGRESS
        """
        status = (request.query_params.get("status") or "").strip().upper()
        ready_unpaid_raw = (request.query_params.get(
            "ready_unpaid") or "").lower()
        ready_unpaid = ready_unpaid_raw in ("1", "true", "yes", "y")

        if not status:
            raise ValidationError(
                {"status": "Required. Example: ?status=READY"})

        allowed = {"CREATED", "IN_PROGRESS", "READY", "PICKED_UP", "CANCELLED"}
        if status not in allowed:
            raise ValidationError(
                {"status": f"Invalid. Allowed: {sorted(list(allowed))}"})

        qs = self.get_queryset().filter(status=status)

        ready_unpaid_mode = None
        if ready_unpaid:
            # Use persisted “settled” balance for fast operator queues.
            # Treat NULL as unknown -> exclude from “unpaid” queue.
            qs = qs.filter(settled_balance_due_cents__gt=0)
            ready_unpaid_mode = "settled_only"

        qs = qs.order_by("-created_at")

        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            resp = self.get_paginated_response(ser.data)
            if ready_unpaid_mode:
                resp["X-Ready-Unpaid-Mode"] = ready_unpaid_mode
                if isinstance(resp.data, dict):
                    resp.data["ready_unpaid_mode"] = ready_unpaid_mode
            return resp

        ser = self.get_serializer(qs, many=True)
        resp = Response(ser.data)
        if ready_unpaid_mode:
            resp["X-Ready-Unpaid-Mode"] = ready_unpaid_mode
        return resp

    @action(detail=False, methods=["get"], url_path="metrics")
    def metrics(self, request):
        """
        GET /api/orders/metrics/
        Operator dashboard snapshot for the current tenant.
        """

        # Tenant timezone (fallback to UTC)
        # Tenant timezone (fallback to UTC)
        tzname = getattr(request.tenant, "timezone", None) or "UTC"
        try:
            tz = ZoneInfo(tzname)
        except Exception:
            tz = ZoneInfo("UTC")

        # Define "today" in tenant-local time (date boundaries)
        now_utc = timezone.now()
        now_local = now_utc.astimezone(tz)
        today_local = now_local.date()

        start_local = datetime(
            today_local.year, today_local.month, today_local.day, 0, 0, 0, tzinfo=tz
        )
        end_local = start_local + timedelta(days=1)

        start = start_local.astimezone(dt_timezone.utc)
        end = end_local.astimezone(dt_timezone.utc)

        # 1) Orders created today
        orders_created_today = Order.objects.filter(
            tenant=request.tenant,
            created_at__gte=start,
            created_at__lt=end,
        ).count()

        # 2) Counts by status (for queues)
        status_counts_qs = (
            Order.objects.filter(tenant=request.tenant)
            .values("status")
            .annotate(count=Count("id"))
        )
        orders_by_status = {row["status"]: row["count"]
                            for row in status_counts_qs}

        # 3) Ready but unpaid (fast) - uses persisted settled_balance_due_cents
        ready_unpaid_count = Order.objects.filter(
            tenant=request.tenant,
            status__in=["READY", "COMPLETED"],
            settled_balance_due_cents__gt=0,
        ).count()

        # 4) Payments today (net)
        # Only CAPTURED counts. Net = IN - OUT.
        pay_qs = Payment.objects.filter(
            tenant=request.tenant,
            status=Payment.Status.CAPTURED,
            created_at__gte=start,
            created_at__lt=end,
        )

        payments_in_cents_today = (
            pay_qs.filter(direction=Payment.Direction.IN)
            .aggregate(s=Sum("amount_cents"))["s"] or 0
        )
        payments_out_cents_today = (
            pay_qs.filter(direction=Payment.Direction.OUT)
            .aggregate(s=Sum("amount_cents"))["s"] or 0
        )

        payments_net_cents_today = int(
            payments_in_cents_today) - int(payments_out_cents_today)

        # 5) Unsettled orders count (useful for cashout/settlement workflows)
        unsettled_orders_count = Order.objects.filter(
            tenant=request.tenant,
            settled_at__isnull=True,
        ).exclude(status="CANCELLED").count()

        return Response({
            "tenant": {"id": request.tenant.id, "slug": request.tenant.slug},
            "timezone": tzname,
            "today": str(today_local),
            "window": {"start": start.isoformat(), "end": end.isoformat()},

            "orders": {
                "created_today": orders_created_today,
                "by_status": orders_by_status,
                "ready_unpaid_count": ready_unpaid_count,
                "unsettled_count": unsettled_orders_count,
            },
            "payments": {
                "in_cents_today": int(payments_in_cents_today),
                "out_cents_today": int(payments_out_cents_today),
                "net_cents_today": int(payments_net_cents_today),
            },
        })

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """
        /api/orders/search/?q=patel
        /api/orders/search/?q=714
        /api/orders/search/?q=1234
        """
        q = (request.query_params.get("q") or "").strip()

        if not q:
            raise ValidationError({"q": "Required. Example: ?q=patel"})

        qs = self.get_queryset()

        sku_order_id = order_id_from_sku(q)
        filters = Q(customer__name__icontains=q) | Q(customer__phone__icontains=q)
        if q.isdigit():
            filters |= Q(id=int(q))
        if sku_order_id is not None:
            filters |= Q(id=sku_order_id)

        qs = qs.filter(filters).select_related("customer")

        qs = qs.order_by("-created_at")
        limit, offset = parse_limit_offset(request, default_limit=20, max_limit=50)
        if limit is not None:
            qs = qs[offset: offset + limit]

        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)

    @action(detail=False, methods=["get"], url_path="cards")
    def cards(self, request):
        """
        GET /api/orders/cards/?q=...&status=...&limit=...&offset=...
        Frontend-friendly order cards.
        """
        qs = (
            Order.objects.filter(tenant=request.tenant)
            .select_related("customer")
            .prefetch_related("payments", "adjustments")
        )

        q = (request.query_params.get("q") or "").strip()
        if q:
            filters = (
                Q(customer__name__icontains=q)
                | Q(customer__phone__icontains=q)
                | Q(customer__email__icontains=q)
            )
            if q.isdigit():
                filters |= Q(id=int(q))
            sku_order_id = order_id_from_sku(q)
            if sku_order_id is not None:
                filters |= Q(id=sku_order_id)
            qs = qs.filter(filters)

        status = (request.query_params.get("status") or "").strip()
        if status:
            qs = qs.filter(status=status)

        qs = qs.order_by("-created_at")
        count = qs.count()

        limit, offset = parse_limit_offset(request, default_limit=50, max_limit=200)
        if limit is not None:
            qs = qs[offset: offset + limit]

        results = []
        for order in qs:
            if order.settled_at is not None:
                if order.settled_total_cents is not None:
                    order.total_cents = order.settled_total_cents
                if order.settled_paid_cents is not None:
                    order.paid_cents = order.settled_paid_cents

            financials = receipt_financials_for_order(order)
            updated_at = max(
                dt for dt in [
                    order.created_at,
                    order.received_at,
                    order.in_progress_at,
                    order.ready_at,
                    order.completed_at,
                    order.cancelled_at,
                    order.picked_up_at,
                    order.settled_at,
                ] if dt is not None
            )

            customer = order.customer
            results.append(
                {
                    "order_id": order.id,
                    "pickup_id": str(order.id),
                    "order_sku": order_sku_for_order(order),
                    "status": order.status,
                    "created_at": order.created_at.isoformat(),
                    "updated_at": updated_at.isoformat() if updated_at else None,
                    "customer": {
                        "id": customer.id if customer else None,
                        "name": getattr(customer, "name", None) if customer else None,
                        "phone": getattr(customer, "phone", None) if customer else None,
                        "email": getattr(customer, "email", None) if customer else None,
                    },
                    "money": {
                        "total_cents": int(order.total_cents or 0),
                        "net_paid_cents": int(financials.get("net_paid_cents") or 0),
                        "balance_due_cents": int(financials.get("balance_due_cents") or 0),
                        "change_due_cents": int(financials.get("change_due_cents") or 0),
                    },
                    "barcode_svg_url": barcode_svg_url(request, order),
                }
            )

        return Response({"count": count, "results": results})

    @action(detail=True, methods=["patch"], url_path="customer")
    def set_customer(self, request, pk=None):
        serializer = OrderCustomerUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer_id = serializer.validated_data.get("customer_id")

        order = self.get_object()
        if customer_id is None:
            order.customer = None
            order.save(update_fields=["customer"])
            return Response({"order_id": order.id, "customer_id": None})

        customer = Customer.objects.filter(
            tenant=self.request.tenant, id=customer_id
        ).first()
        if customer is None:
            raise NotFound()

        order.customer = customer
        order.save(update_fields=["customer"])
        return Response({"order_id": order.id, "customer_id": customer.id})


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return OrderItem.objects.filter(order__tenant=self.request.tenant)

    def perform_create(self, serializer):
        order = serializer.validated_data["order"]
        item = serializer.validated_data["item"]

        if order.tenant_id != self.request.tenant.id:
            raise ValidationError(
                {"order": "Order does not belong to this tenant."})

        if item.tenant_id != self.request.tenant.id:
            raise ValidationError(
                {"item": "Inventory item does not belong to this tenant."})

        if order.status == "PICKED_UP":
            raise ValidationError(
                {"order": "Cannot modify items after pickup."})
        if order.settled_at is not None:
            raise ValidationError(
                {"order": "Cannot modify items after settlement."})

        serializer.save(tenant=self.request.tenant)
        recalc_order_totals(order)

    def perform_update(self, serializer):
        order_item = serializer.instance
        order = order_item.order

        if order.status == "PICKED_UP":
            raise ValidationError(
                {"order": "Cannot modify items after pickup."})
        if order.settled_at is not None:
            raise ValidationError(
                {"order": "Cannot modify items after settlement."})

        order_item = serializer.save()
        recalc_order_totals(order_item.order)

    def perform_destroy(self, instance):
        order = instance.order

        if order.status == "PICKED_UP":
            raise ValidationError(
                {"order": "Cannot modify items after pickup."})
        if order.settled_at is not None:
            raise ValidationError(
                {"order": "Cannot modify items after settlement."})

        super().perform_destroy(instance)
        recalc_order_totals(order)
