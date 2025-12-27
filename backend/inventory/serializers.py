from rest_framework import serializers
from .models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "name", "sku",
                  "unit_price_cents", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
