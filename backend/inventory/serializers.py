from rest_framework import serializers
from .models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True, write_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        return obj.image.url

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "sku",
            "image",
            "image_url",
            "unit_price_cents",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "image_url", "created_at"]
