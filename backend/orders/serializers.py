# orders/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusEvent
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
    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "status",
            "due_at",
            "notes",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
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
            if a.direction == Adjustment.Direction.IN:
                net += int(a.amount_cents)
            else:
                net -= int(a.amount_cents)
        return net

    def get_net_paid_cents(self, obj):
        return int(obj.paid_cents) + int(self.get_adjustments_net_cents(obj))

    def get_balance_due_cents(self, obj):
        return max(int(obj.total_cents) - int(self.get_net_paid_cents(obj)), 0)

    def get_change_due_cents(self, obj):
        return max(int(self.get_net_paid_cents(obj)) - int(obj.total_cents), 0)
