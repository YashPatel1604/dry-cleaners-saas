from rest_framework.exceptions import ValidationError
from .services import recalc_order_totals
from .models import OrderItem, Order
from inventory.models import InventoryItem
from .serializers import OrderItemSerializer
from .models import OrderItem
from rest_framework import viewsets, permissions


from .models import Order
from .serializers import OrderSerializer
from customers.models import Customer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(tenant=self.request.tenant).select_related("customer")

    def perform_create(self, serializer):
        customer_id = serializer.validated_data["customer"].id

        # ensure customer belongs to the same tenant (hard isolation)
        if not Customer.objects.filter(id=customer_id, tenant=self.request.tenant).exists():
            raise ValidationError(
                {"customer": "Customer does not belong to this tenant."})

        serializer.save(tenant=self.request.tenant)


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
