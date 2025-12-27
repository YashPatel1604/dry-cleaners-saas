from rest_framework import serializers
from .models import Order, OrderItem

ORDER_STATUS_TRANSITIONS = {
    "RECEIVED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"READY", "CANCELLED"},
    "READY": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
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
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
        ]

    def validate(self, attrs):
        # Only enforce transitions on update
        instance = getattr(self, "instance", None)
        if not instance:
            return attrs

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
        # if quantity or item changes, recompute prices
        item = validated_data.get("item", instance.item)
        quantity = validated_data.get("quantity", instance.quantity)

        validated_data["unit_price_cents"] = item.unit_price_cents
        validated_data["line_total_cents"] = quantity * item.unit_price_cents

        return super().update(instance, validated_data)
