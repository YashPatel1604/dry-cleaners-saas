from django.urls import path
from .views import (
    TenantCreateView,
    TenantMeView,
    TenantDefaultsView,
    TenantBootstrapView,
    TenantInvitesView,
    TenantInviteRevokeView,
)

urlpatterns = [
    path("", TenantCreateView.as_view(), name="tenant-create"),
    path("me/", TenantMeView.as_view(), name="tenant-me"),
    path("defaults/", TenantDefaultsView.as_view(), name="tenant-defaults"),
    path("bootstrap/", TenantBootstrapView.as_view(), name="tenant-bootstrap"),
    path("invites/", TenantInvitesView.as_view(), name="tenant-invites"),
    path("invites/<int:invite_id>/revoke/", TenantInviteRevokeView.as_view(), name="tenant-invite-revoke"),
]
