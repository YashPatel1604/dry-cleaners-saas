"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.http import JsonResponse
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from tenants.views import (
    TenantSettingsView,
    MeView,
    MeTenantsView,
    TenantMembershipsView,
    TenantMembershipDetailView,
    InviteAcceptView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/tenants/", include("tenants.urls")),
    path("api/tenant/", include("tenants.urls")),
    path("api/tenant/", include("customers.urls")),
    path("api/tenant/settings/", TenantSettingsView.as_view(), name="tenant-settings"),
    path("api/tenant/memberships/", TenantMembershipsView.as_view(), name="tenant-memberships"),
    path("api/tenant/memberships/<int:user_id>/", TenantMembershipDetailView.as_view(), name="tenant-membership-detail"),
    path("api/me/", MeView.as_view(), name="me"),
    path("api/me/tenants/", MeTenantsView.as_view(), name="me-tenants"),
    path("api/invites/accept/", InviteAcceptView.as_view(), name="invite-accept"),

    path("api/", include("customers.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("inventory.urls")),
    path("api/", include("payments.urls")),
    path("api/", include("dashboard.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/ai/", include("ai.urls")),


    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"),
         name="swagger-ui"),
]


# config/urls.py (or any urls module)


def debug_headers(request):
    return JsonResponse({
        "path": request.path,
        "META_HTTP_X_TENANT": request.META.get("HTTP_X_TENANT"),
        "headers_X_Tenant": request.headers.get("X-Tenant"),
        "all_http_headers": {k: v for k, v in request.META.items() if k.startswith("HTTP_")},
    })


urlpatterns += [
    path("debug/headers/", debug_headers),
]
