# orders/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusEvent, OrderNote
from payments.models import Payment, Adjustment
from customers.models import Customer


ORDER_STATUS_TRANSITIONS = {
    "RECEIVED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"READY", "CANCELLED"},
    "READY": {"COMPLETED", "PICKED_UP", "CANCELLED"},
    "COMPLETED": {"PICKED_UP"},
    "PICKED_UP": set(),
    "CANCELLED": set(),
}


class OrderSerializer(serializers.ModelSerializer):
    net_paid_cents = serializers.SerializerMethodField()
    balance_due_cents = serializers.SerializerMethodField()
    change_due_cents = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="customer.name", read_only=True, allow_null=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True, allow_null=True)
    customer_email = serializers.CharField(source="customer.email", read_only=True, allow_null=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "customer_email",
            "status",
            "due_at",
            "notes",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
            "net_paid_cents",
            "balance_due_cents",
            "change_due_cents",
            "settled_at",
            "created_at",
            "received_at", "in_progress_at", "ready_at", "completed_at", "cancelled_at", "picked_up_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
            "net_paid_cents",
            "balance_due_cents",
            "change_due_cents",
            "customer_name",
            "customer_phone",
            "customer_email",
            "settled_at", "received_at", "in_progress_at", "ready_at", "completed_at", "cancelled_at", "picked_up_at",
        ]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        if not instance:
            return attrs

        if instance.settled_at and "status" in attrs and attrs["status"] != instance.status:
            raise serializers.ValidationError(
                {"status": "Cannot change status after settlement."})

        if "status" in attrs:
            old = instance.status
            new = attrs["status"]
            if old != new:
                allowed = ORDER_STATUS_TRANSITIONS.get(old, set())
                if new not in allowed:
                    raise serializers.ValidationError({
                        "status": f"Invalid status transition: {old} -> {new}. Allowed: {sorted(allowed)}"
                    })

        return attrs

    def _receipt_financials(self, obj):
        cached = getattr(obj, "_receipt_financials_cache", None)
        if cached is None:
            from .services import receipt_financials_for_order
            cached = receipt_financials_for_order(obj)
            setattr(obj, "_receipt_financials_cache", cached)
        return cached

    def get_net_paid_cents(self, obj):
        return self._receipt_financials(obj)["net_paid_cents"]

    def get_balance_due_cents(self, obj):
        return self._receipt_financials(obj)["balance_due_cents"]

    def get_change_due_cents(self, obj):
        return self._receipt_financials(obj)["change_due_cents"]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "item",
            "quantity",
            "unit_price_cents",
            "line_total_cents",
            "created_at",
        ]
        read_only_fields = ["id", "unit_price_cents",
                            "line_total_cents", "created_at"]

    def create(self, validated_data):
        item = validated_data["item"]
        quantity = validated_data["quantity"]

        validated_data["unit_price_cents"] = item.unit_price_cents
        validated_data["line_total_cents"] = quantity * item.unit_price_cents

        return super().create(validated_data)

    def update(self, instance, validated_data):
        item = validated_data.get("item", instance.item)
        quantity = validated_data.get("quantity", instance.quantity)

        validated_data["unit_price_cents"] = item.unit_price_cents
        validated_data["line_total_cents"] = quantity * item.unit_price_cents

        return super().update(instance, validated_data)


class OrderStatusEventSerializer(serializers.ModelSerializer):
    changed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusEvent
        fields = [
            "id",
            "from_status",
            "to_status",
            "changed_by_email",
            "note",
            "created_at",
        ]

    def get_changed_by_email(self, obj):
        u = obj.changed_by
        return getattr(u, "email", None) if u else None


class OrderCustomerUpdateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False, allow_null=True)


class OrderNoteSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(source="author.id", read_only=True, allow_null=True)
    author_username = serializers.CharField(source="author.username", read_only=True, allow_null=True)

    class Meta:
        model = OrderNote
        fields = ["id", "note", "created_at", "author_id", "author_username"]


# -----------------------------
# Receipt serializers
# -----------------------------

class ReceiptCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "email"]


class ReceiptItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    sku = serializers.CharField(source="item.sku", read_only=True, default="")

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "item",
            "item_name",
            "sku",
            "quantity",
            "unit_price_cents",
            "line_total_cents",
        ]


class ReceiptPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "method",
            "status",
            "direction",
            "amount_cents",
            "reference",
            "note",
            "created_at",
        ]


class ReceiptAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adjustment
        fields = [
            "id",
            "kind",
            "status",
            "direction",
            "amount_cents",
            "reference",
            "note",
            "created_at",
        ]


class OrderReceiptSerializer(serializers.ModelSerializer):
    customer = ReceiptCustomerSerializer(read_only=True)
    items = ReceiptItemSerializer(many=True, read_only=True)
    payments = ReceiptPaymentSerializer(many=True, read_only=True)

    # ✅ new (if not already)
    adjustments = serializers.SerializerMethodField()
    adjustments_net_cents = serializers.SerializerMethodField()
    net_paid_cents = serializers.SerializerMethodField()

    balance_due_cents = serializers.SerializerMethodField()
    change_due_cents = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "due_at",
            "notes",
            "created_at",
            "settled_at",
            "customer",
            "items",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
            "adjustments_net_cents",
            "net_paid_cents",
            "balance_due_cents",
            "change_due_cents",
            "payments",
            "adjustments",
        ]

    def get_adjustments(self, obj):
        # assumes related_name="adjustments" on Adjustment.order FK
        qs = getattr(obj, "adjustments", None)
        if qs is None:
            return []
        return ReceiptAdjustmentSerializer(qs.all(), many=True).data

    def get_adjustments_net_cents(self, obj):
        qs = getattr(obj, "adjustments", None)
        if qs is None:
            return 0
        net = 0
        for a in qs.all():
            if a.status != Adjustment.Status.APPLIED:
                continue
            amt = int(a.amount_cents or 0)
            if a.direction == Adjustment.Direction.IN:
                net += amt
            else:
                net -= amt
        return net

    def get_net_paid_cents(self, obj):
        return int(getattr(obj, "paid_cents", 0) or 0) + int(self.get_adjustments_net_cents(obj) or 0)

    def get_balance_due_cents(self, obj):
        total = int(getattr(obj, "total_cents", 0) or 0)
        net_paid = int(self.get_net_paid_cents(obj) or 0)
        return max(total - net_paid, 0)

    def get_change_due_cents(self, obj):
        """
        Option A (explicit OUT for change):
        - If there is a captured OUT cash payment (change/refund), then "change due" is 0
        because the drawer already recorded the payout.
        - Otherwise, show overpayment (net_paid - total) so the counter knows change is owed.
        """
        # If we already recorded an OUT payment, we don't want the receipt to still say "change due"
        try:
            payments_qs = getattr(obj, "payments", None)
            if payments_qs is not None:
                prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("payments")
                if prefetched is not None:
                    for p in prefetched:
                        if p.status == Payment.Status.CAPTURED and p.direction == Payment.Direction.OUT:
                            return 0
                else:
                    has_captured_out = payments_qs.filter(
                        status=Payment.Status.CAPTURED,
                        direction=Payment.Direction.OUT,
                    ).exists()
                    if has_captured_out:
                        return 0
        except Exception:
            pass

        net_paid = int(self.get_net_paid_cents(obj) or 0)

        # Prefer settlement snapshot totals if settled (reprint-stable),
        # otherwise use current total (NULL-safe).
        if getattr(obj, "settled_at", None) is not None:
            total_raw = getattr(obj, "settled_total_cents", None)
        else:
            total_raw = getattr(obj, "total_cents", None)

        total = int(total_raw or 0)
        return max(net_paid - total, 0)
