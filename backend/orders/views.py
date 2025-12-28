# orders/views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from customers.models import Customer, normalize_phone_us

from .models import Order, OrderItem, OrderStatusEvent
from .serializers import (
    OrderSerializer,
    OrderItemSerializer,
    OrderReceiptSerializer,
    OrderStatusEventSerializer,
)
from .services import recalc_order_totals


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
            order = serializer.save(
                tenant=self.request.tenant,
                received_at=timezone.now(),  # ✅ new field on Order
            )

            # optional but recommended: timeline starts here
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
            # lock the row to serialize concurrent updates
            locked = Order.objects.select_for_update().get(
                pk=serializer.instance.pk,
                tenant=self.request.tenant,
            )

            old_status = locked.status
            new_status = serializer.validated_data.get("status", old_status)

            order = serializer.save()

            if old_status != new_status:
                # ✅ audit event
                OrderStatusEvent.objects.create(
                    tenant=self.request.tenant,
                    order=order,
                    from_status=old_status,
                    to_status=new_status,
                    changed_by=self.request.user if self.request.user.is_authenticated else None,)

                # ✅ per-state timestamp (set only once)
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
            fields=["subtotal_cents", "tax_cents",
                    "total_cents", "paid_cents", "settled_at"]
        )

        return Response(OrderReceiptSerializer(order).data)

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
            # idempotent settle: return receipt-like payload as-is
            data = OrderReceiptSerializer(order).data
            return Response(data)

        # Ensure totals/paid are current
        recalc_order_totals(order)
        order.refresh_from_db(fields=["total_cents", "paid_cents"])

        if int(order.paid_cents) < int(order.total_cents):
            return Response({"order": "Order has balance due and cannot be settled."}, status=400)

        # Snapshot values at settlement time (ignore adjustments entirely here)
        settled_total = int(order.total_cents)
        settled_paid = int(order.paid_cents)
        settled_change = max(settled_paid - settled_total, 0)
        settled_balance_due = max(settled_total - settled_paid, 0)

        with transaction.atomic():
            # Lock row so two settle requests can't race
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

        # Return receipt-style response after settle
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
            tenant=request.tenant,
            order=order,
        ).order_by("created_at")

        return Response(OrderStatusEventSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="set_customer")
    def set_customer(self, request, pk=None):
        """
        POST /api/orders/{id}/set_customer { "customer_id": "..." }
        """
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
        """
        POST /api/orders/{id}/set_customer_by_phone
        {
          "phone": "...",
          "name": "...",   (required if creating)
          "email": "...",
          "notes": "..."
        }
        """
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
            tenant=request.tenant,
            phone_e164=phone_e164,
        ).first()

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

        serializer.save(tenant=self.request.tenant)
        recalc_order_totals(order)

    def perform_update(self, serializer):
        order_item = serializer.save()
        recalc_order_totals(order_item.order)

    def perform_destroy(self, instance):
        order = instance.order
        super().perform_destroy(instance)
        recalc_order_totals(order)
