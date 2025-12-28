# payments/serializers.py
from rest_framework import serializers
from .models import Payment, Adjustment
from orders.models import Order


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "method",
            "status",
            "direction",
            "amount_cents",
            "reference",
            "note",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]


class AdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adjustment
        fields = [
            "id",
            "order",
            "kind",
            "status",
            "direction",
            "amount_cents",
            "reference",
            "note",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_amount_cents(self, v):
        if v is None or int(v) <= 0:
            raise serializers.ValidationError("Must be > 0.")
        return v
