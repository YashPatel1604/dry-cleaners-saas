from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from django.db.models import Q
import re

from .models import Customer, normalize_phone_us
from .serializers import (
    CustomerListSerializer,
    CustomerDetailSerializer,
    CustomerCreateUpdateSerializer,
)
from django.utils import timezone
from orders.models import Order, OrderStatusEvent
from orders.utils import default_due_at_for_tenant
from tenants.permissions import IsTenantMember
from tenants.utils import parse_limit_offset


class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTenantMember]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CustomerCreateUpdateSerializer
        if self.action == "retrieve":
            return CustomerDetailSerializer
        return CustomerListSerializer

    def get_queryset(self):
        return Customer.objects.filter(tenant=self.request.tenant).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save(tenant=self.request.tenant)
        return Response(
            CustomerDetailSerializer(customer).data,
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        limit, offset = parse_limit_offset(request, default_limit=None, max_limit=200)
        if limit is not None:
            qs = qs[offset: offset + limit]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        return Response(CustomerDetailSerializer(customer).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="lookup")
    def lookup(self, request):
        """
        GET /api/customers/lookup?phone=7148788441
        200 -> customer, 404 -> not found
        """
        raw = (request.query_params.get("phone") or "").strip()
        if not raw:
            raise ValidationError({"phone": "phone query param is required"})

        phone_e164 = normalize_phone_us(raw)
        if not phone_e164:
            raise ValidationError(
                {"phone": "Invalid/unsupported phone format"})

        customer = Customer.objects.filter(
            tenant=request.tenant,
            phone_e164=phone_e164,
        ).first()

        if not customer:
            return Response({"detail": "Not found"}, status=404)

        return Response(CustomerDetailSerializer(customer).data)

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """
        GET /api/customers/search?q=patel
        Searches name/phone/email (tenant-scoped). Returns top 20.
        """
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response([])

        digits = re.sub(r"\D+", "", q)
        phone_e164 = normalize_phone_us(q)

        filters = Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        if phone_e164:
            filters |= Q(phone_e164=phone_e164)
        if digits:
            filters |= Q(phone__icontains=digits) | Q(phone_e164__icontains=digits)
            if len(digits) == 4:
                filters |= Q(phone__endswith=digits) | Q(phone_e164__endswith=digits)

        limit, offset = parse_limit_offset(request, default_limit=20, max_limit=50)

        qs = (
            Customer.objects.filter(tenant=request.tenant)
            .filter(filters)
            .order_by("-updated_at")
        )

        if limit is not None:
            qs = qs[offset: offset + limit]
        return Response(CustomerListSerializer(qs, many=True).data)

    @action(detail=True, methods=["get", "post"], url_path="orders")
    def orders(self, request, pk=None):
        """
        GET /api/customers/{id}/orders?limit=25&offset=0
        Customer order history (tenant-safe)
        """
        customer = Customer.objects.filter(
            tenant=request.tenant, pk=pk).first()
        if not customer:
            raise NotFound()

        if request.method.lower() == "post":
            due_at = default_due_at_for_tenant(request.tenant)
            order = Order.objects.create(
                tenant=request.tenant,
                customer=customer,
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
            return Response(
                {
                    "order_id": order.id,
                    "pickup_id": str(order.id),
                    "status": order.status,
                },
                status=201,
            )

        limit = int(request.query_params.get("limit", 25))
        offset = int(request.query_params.get("offset", 0))
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        qs = (
            Order.objects.filter(tenant=request.tenant, customer=customer)
            .select_related("customer")
            .order_by("-created_at")
        )

        total = qs.count()
        page = qs[offset: offset + limit]

        # Slim payload (hand-picked fields)
        results = [
            {
                "id": o.id,
                "status": o.status,
                "created_at": o.created_at,
                "due_at": o.due_at,
                "subtotal_cents": o.subtotal_cents,
                "tax_cents": o.tax_cents,
                "total_cents": o.total_cents,
                "paid_cents": o.paid_cents,
                "settled_at": o.settled_at,
                "notes": o.notes,
            }
            for o in page
        ]

        return Response({"count": total, "limit": limit, "offset": offset, "results": results})
