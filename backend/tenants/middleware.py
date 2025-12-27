from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .models import Tenant


class TenantMiddleware(MiddlewareMixin):
    HEADER_NAME = "HTTP_X_TENANT"  # X-Tenant -> HTTP_X_TENANT

    def process_request(self, request):
        OPEN_PATH_PREFIXES = (
            "/admin",
            "/api/docs",
            "/api/schema",
            "/api/auth",
        )

        OPEN_EXACT_PATHS = (
            "/api/tenants/",   # allow POST create (and maybe list if you want)
        )

        if request.path.startswith(OPEN_PATH_PREFIXES) or request.path in OPEN_EXACT_PATHS:
            request.tenant = None
            return None

        slug = request.META.get(self.HEADER_NAME)
        if not slug:
            return JsonResponse({"detail": "Missing X-Tenant header."}, status=400)

        try:
            tenant = Tenant.objects.get(slug=slug, is_active=True)
        except Tenant.DoesNotExist:
            return JsonResponse({"detail": "Invalid X-Tenant."}, status=400)

        request.tenant = tenant
        return None
