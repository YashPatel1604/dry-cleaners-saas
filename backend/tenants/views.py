from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from .models import Tenant, TenantConfigEvent
from .serializers import TenantSerializer, TenantCreateSerializer, TenantDefaultsSerializer
from .permissions import IsTenantMember, IsTenantAdmin, get_active_membership
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


class TenantCreateView(generics.CreateAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantCreateSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="X-Tenant",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Tenant slug (e.g. store-1)"
        )
    ]
)
class TenantMeView(generics.RetrieveAPIView):
    serializer_class = TenantSerializer
    permission_classes = [IsTenantMember]

    def get_object(self):
        return self.request.tenant


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="X-Tenant",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Tenant slug (e.g. store-1)"
        )
    ]
)
class TenantDefaultsView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/tenants/defaults/
    PATCH /api/tenants/defaults/
    Updates the tenant's default pickup promise settings.
    """
    serializer_class = TenantDefaultsSerializer
    permission_classes = [IsTenantMember]

    def get_object(self):
        return self.request.tenant


class TenantSettingsView(APIView):
    permission_classes = [IsTenantAdmin]

    def patch(self, request):
        tenant = request.tenant
        updates = {}
        events = []

        if "collects_tax" in request.data:
            raw_collects_tax = request.data.get("collects_tax")
            if isinstance(raw_collects_tax, bool):
                collects_tax = raw_collects_tax
            elif isinstance(raw_collects_tax, str):
                normalized = raw_collects_tax.strip().lower()
                if normalized in ("true", "1", "yes", "y"):
                    collects_tax = True
                elif normalized in ("false", "0", "no", "n"):
                    collects_tax = False
                else:
                    raise ValidationError(
                        {"collects_tax": "Must be a boolean."}
                    )
            else:
                collects_tax = bool(raw_collects_tax)
            if tenant.collects_tax != collects_tax:
                events.append(
                    TenantConfigEvent(
                        tenant=tenant,
                        actor=request.user,
                        key="collects_tax",
                        old_value=str(tenant.collects_tax),
                        new_value=str(collects_tax),
                    )
                )
                updates["collects_tax"] = collects_tax

        if "tax_rate_bps" in request.data:
            try:
                tax_rate_bps = int(request.data.get("tax_rate_bps"))
            except Exception as exc:
                raise ValidationError({"tax_rate_bps": "Must be an integer."}) from exc
            if tax_rate_bps < 0 or tax_rate_bps > 2000:
                raise ValidationError(
                    {"tax_rate_bps": "Must be between 0 and 2000."}
                )
            if tenant.tax_rate_bps != tax_rate_bps:
                events.append(
                    TenantConfigEvent(
                        tenant=tenant,
                        actor=request.user,
                        key="tax_rate_bps",
                        old_value=str(tenant.tax_rate_bps),
                        new_value=str(tax_rate_bps),
                    )
                )
                updates["tax_rate_bps"] = tax_rate_bps

        if updates:
            for key, value in updates.items():
                setattr(tenant, key, value)
            tenant.save(update_fields=list(updates.keys()))
            TenantConfigEvent.objects.bulk_create(events)

        return Response(
            {
                "tenant": {"id": tenant.id, "slug": tenant.slug},
                "collects_tax": tenant.collects_tax,
                "tax_rate_bps": tenant.tax_rate_bps,
            }
        )


class MeView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        membership = get_active_membership(
            user=request.user, tenant=request.tenant, request=request
        )
        return Response(
            {
                "user": {"id": request.user.id, "username": request.user.username},
                "tenant": {"id": request.tenant.id, "slug": request.tenant.slug},
                "role": membership.role if membership else None,
            }
        )
