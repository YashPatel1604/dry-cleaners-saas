# orders/views.py
from datetime import timedelta, datetime

from django.db import transaction
from django.utils import timezone

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from customers.models import Customer, normalize_phone_us
from payments.models import Payment, Adjustment
from payments.serializers import PaymentSerializer
from audit.models import AuditEvent
from .services import recalc_order_totals
from django.db import IntegrityError
from django.db.models import Q

from .models import Order, OrderItem, OrderStatusEvent
from .serializers import (
    OrderSerializer,
    OrderItemSerializer,
    OrderReceiptSerializer,
    OrderStatusEventSerializer,
)


def default_due_at_for_tenant(tenant, now=None):
    """
    Compute default pickup promise using tenant settings:
    localdate(now) + default_turnaround_days at (default_ready_hour:default_ready_minute).
    """
    if now is None:
        now = timezone.now()

    due_day = timezone.localdate(
        now) + timedelta(days=int(tenant.default_turnaround_days or 0))

    hour = int(getattr(tenant, "default_ready_hour", 17) or 17)
    minute = int(getattr(tenant, "default_ready_minute", 0) or 0)

    tz = timezone.get_current_timezone()
    return timezone.make_aware(
        datetime(due_day.year, due_day.month, due_day.day, hour, minute, 0),
        tz
    )


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


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # keep list/retrieve fast
        return Order.objects.filter(tenant=self.request.tenant).select_related("customer")

    def perform_create(self, serializer):
        customer_id = serializer.validated_data["customer"].id

        if not Customer.objects.filter(id=customer_id, tenant=self.request.tenant).exists():
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
        order.refresh_from_db(
            fields=["subtotal_cents", "tax_cents", "total_cents", "paid_cents", "settled_at"])

        return Response(OrderReceiptSerializer(order).data)

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

        allow_balance_due = bool(request.data.get(
            "allow_balance_due", default_allow))

        order = (
            Order.objects.filter(tenant=request.tenant, pk=pk)
            .select_related("customer")
            .prefetch_related("payments", "adjustments", "items__item")
            .first()
        )
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

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

            locked.save(update_fields=["status", "picked_up_at"])

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
            return Response(data)

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
                return Response(data)

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

    @action(detail=True, methods=["post"], url_path="set_customer")
    def set_customer(self, request, pk=None):
        customer_id = request.data.get("customer_id")
        if not customer_id:
            raise ValidationError({"customer_id": "Required"})

        order = Order.objects.filter(tenant=request.tenant, pk=pk).first()
        if not order:
            raise ValidationError({"order": "Order not found in this tenant."})

        customer = Customer.objects.filter(
            tenant=request.tenant, pk=customer_id).first()
        if not customer:
            raise ValidationError(
                {"customer": "Customer not found in this tenant."})

        order.customer = customer
        order.save(update_fields=["customer"])

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

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        order = self.get_object()

        # safety: tenant isolation (should already be enforced by get_queryset/get_object)
        if order.tenant_id != request.tenant.id:
            raise ValidationError(
                {"order": "Order does not belong to this tenant."})

        payment_ids = list(
            Payment.objects.filter(
                tenant=request.tenant, order_id=order.id).values_list("id", flat=True)
        )
        adjustment_ids = list(
            Adjustment.objects.filter(
                tenant=request.tenant, order_id=order.id).values_list("id", flat=True)
        )

        qs = AuditEvent.objects.filter(tenant=request.tenant).filter(
            Q(entity_type="order", entity_id=str(order.id))
            | Q(entity_type="payment", entity_id__in=[str(i) for i in payment_ids])
            | Q(entity_type="adjustment", entity_id__in=[str(i) for i in adjustment_ids])
        ).order_by("created_at")

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

        return Response(
            {
                "order_id": order.id,
                "count": len(data),
                "events": data,
            }
        )

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

        if ready_unpaid:
            # Use persisted “settled” balance for fast operator queues.
            # Treat NULL as unknown -> exclude from “unpaid” queue.
            qs = qs.filter(settled_balance_due_cents__gt=0)

        qs = qs.order_by("-created_at")

        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)

        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)
    
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

        qs = qs.filter(
            Q(customer__name__icontains=q)
            | Q(customer__phone__icontains=q)
            | Q(id__icontains=q)
        ).select_related("customer")

        qs = qs.order_by("-created_at")[:20]  # hard cap for counter speed

        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

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
