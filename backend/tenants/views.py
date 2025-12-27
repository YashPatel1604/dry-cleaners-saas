from rest_framework import generics, permissions
from .models import Tenant
from .serializers import TenantSerializer, TenantCreateSerializer
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
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.tenant
