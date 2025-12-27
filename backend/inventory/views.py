from rest_framework import viewsets, permissions
from .models import InventoryItem
from .serializers import InventoryItemSerializer
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError


class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InventoryItem.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        try:
            serializer.save(tenant=self.request.tenant)
        except IntegrityError:
            # matches your unique constraint (tenant, name)
            raise ValidationError(
                {"name": "Inventory item with this name already exists for this tenant."})
