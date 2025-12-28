from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Q

from .models import Customer, normalize_phone_us
from .serializers import CustomerSerializer
from orders.models import Order


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Customer.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

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

        return Response(CustomerSerializer(customer).data)

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """
        GET /api/customers/search?q=patel
        Searches name/phone/email (tenant-scoped). Returns top 20.
        """
        q = (request.query_params.get("q") or "").strip()
        if not q:
            return Response([])

        phone_e164 = normalize_phone_us(q)

        filters = Q(name__icontains=q) | Q(
            email__icontains=q) | Q(phone__icontains=q)
        if phone_e164:
            filters |= Q(phone_e164=phone_e164)

        qs = (
            Customer.objects.filter(tenant=request.tenant)
            .filter(filters)
            .order_by("-created_at")[:20]
        )

        return Response(CustomerSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="orders")
    def orders(self, request, pk=None):
        """
        GET /api/customers/{id}/orders?limit=25&offset=0
        Customer order history (tenant-safe)
        """
        limit = int(request.query_params.get("limit", 25))
        offset = int(request.query_params.get("offset", 0))
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        customer = Customer.objects.filter(
            tenant=request.tenant, pk=pk).first()
        if not customer:
            raise ValidationError({"customer": "Not found in this tenant"})

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
