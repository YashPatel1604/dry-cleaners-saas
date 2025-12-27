from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TenantHeaderExtension(OpenApiAuthenticationExtension):
    """
    Adds X-Tenant header to the OpenAPI security scheme list so Swagger UI can send it.
    """
    target_class = "rest_framework.authentication.BaseAuthentication"
    name = "tenantHeader"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-Tenant",
            "description": "Tenant slug (location). Example: irvine-main",
        }
