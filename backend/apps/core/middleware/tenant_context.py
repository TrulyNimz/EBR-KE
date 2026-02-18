"""
Middleware to inject tenant context and validate module access.
"""
from django.utils.deprecation import MiddlewareMixin
from rest_framework.exceptions import PermissionDenied


class TenantContextMiddleware(MiddlewareMixin):
    """
    Middleware to:
    1. Add enabled modules to request
    2. Add tenant settings to request
    3. Validate module access for API requests
    """

    # Module path prefixes
    MODULE_PATHS = {
        '/api/v1/healthcare/': 'healthcare',
        '/api/v1/manufacturing/': 'manufacturing',
        '/api/v1/agriculture/': 'agriculture',
    }

    def process_request(self, request):
        """Add tenant context to request."""
        if hasattr(request, 'tenant') and request.tenant:
            tenant = request.tenant

            # Add enabled modules to request
            request.enabled_modules = tenant.enabled_modules or []

            # Add tenant settings
            if hasattr(tenant, 'extended_settings'):
                request.tenant_settings = tenant.extended_settings

            # Validate module access for API requests
            if request.path.startswith('/api/'):
                self._validate_module_access(request)

    def _validate_module_access(self, request):
        """Validate that tenant has access to requested module."""
        for path_prefix, module in self.MODULE_PATHS.items():
            if request.path.startswith(path_prefix):
                if module not in request.enabled_modules:
                    raise PermissionDenied(
                        detail=f"Module '{module}' is not enabled for this organization."
                    )
