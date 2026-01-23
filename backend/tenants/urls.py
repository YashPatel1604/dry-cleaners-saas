from django.urls import path
from .views import (
    TenantCreateView,
    TenantMeView,
    TenantDefaultsView,
    TenantBootstrapView,
    TenantInvitesView,
    TenantInviteRevokeView,
    TenantMembershipAuditView,
    TenantConfigAuditView,
    TenantInviteAuditView,
    TenantDeactivateView,
    TenantReportsSummaryView,
    TenantReportsRangeView,
    TenantReportsUnpaidView,
)

urlpatterns = [
    path("", TenantCreateView.as_view(), name="tenant-create"),
    path("me/", TenantMeView.as_view(), name="tenant-me"),
    path("defaults/", TenantDefaultsView.as_view(), name="tenant-defaults"),
    path("bootstrap/", TenantBootstrapView.as_view(), name="tenant-bootstrap"),
    path("invites/", TenantInvitesView.as_view(), name="tenant-invites"),
    path("invites/<int:invite_id>/revoke/", TenantInviteRevokeView.as_view(), name="tenant-invite-revoke"),
    path("audit/memberships/", TenantMembershipAuditView.as_view(), name="tenant-audit-memberships"),
    path("audit/config/", TenantConfigAuditView.as_view(), name="tenant-audit-config"),
    path("audit/invites/", TenantInviteAuditView.as_view(), name="tenant-audit-invites"),
    path("deactivate/", TenantDeactivateView.as_view(), name="tenant-deactivate"),
    path("reports/summary/", TenantReportsSummaryView.as_view(), name="tenant-reports-summary"),
    path("reports/range/", TenantReportsRangeView.as_view(), name="tenant-reports-range"),
    path("reports/unpaid/", TenantReportsUnpaidView.as_view(), name="tenant-reports-unpaid"),
]
