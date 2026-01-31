from rest_framework.permissions import BasePermission
from rest_framework.exceptions import NotFound

from .models import TenantMembership


def get_active_membership(*, user, tenant, request=None):
    if request is not None and hasattr(request, "_tenant_membership_cached"):
        return request._tenant_membership_cached

    membership = None
    if user is not None and user.is_authenticated and tenant is not None:
        membership = (
            TenantMembership.objects.filter(
                tenant=tenant, user=user, is_active=True
            )
            .only("id", "role")
            .first()
        )

    if request is not None:
        request._tenant_membership_cached = membership

    return membership


class IsTenantMember(BasePermission):
    message = "Not found."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        membership = get_active_membership(
            user=request.user, tenant=getattr(request, "tenant", None), request=request
        )
        if membership is None:
            raise NotFound()
        return True


class IsTenantAdmin(BasePermission):
    message = "Not found."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        membership = get_active_membership(
            user=request.user, tenant=getattr(request, "tenant", None), request=request
        )
        if membership is None or membership.role != TenantMembership.Role.OWNER_ADMIN:
            raise NotFound()
        return True
