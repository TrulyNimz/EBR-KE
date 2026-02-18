"""
Custom permission classes for the EBR Platform.
"""
from rest_framework.permissions import BasePermission


class RBACPermission(BasePermission):
    """
    Role-Based Access Control permission class.

    Checks if the authenticated user has the required permission
    through their assigned roles.

    Usage in views:
        class MyView(APIView):
            permission_classes = [RBACPermission]
            required_permission = 'batch_records.batch.create'
    """
    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        """Check if user has the required permission."""
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers and staff bypass RBAC (they can do everything)
        if request.user.is_superuser or request.user.is_staff:
            return True

        # Allow if no specific permission required
        required_permission = getattr(view, 'required_permission', None)
        if not required_permission:
            return True

        # Check user permissions via assigned roles
        user_permissions = request.user.get_all_permissions_set()
        return required_permission in user_permissions

    def has_object_permission(self, request, view, obj):
        """Check object-level permission with scope awareness."""
        required_permission = getattr(view, 'required_permission', None)
        if not required_permission:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        # First check if user has the permission at all
        if not self.has_permission(request, view):
            return False

        # Check scoped permissions if object has scope
        # This would be expanded based on your scope requirements
        return True


class IsAdminUser(BasePermission):
    """
    Permission class for admin-only access.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_staff
        )


class ModulePermission(BasePermission):
    """
    Permission class to check if tenant has a module enabled.

    Usage:
        class HealthcareView(APIView):
            permission_classes = [ModulePermission]
            required_module = 'healthcare'
    """
    message = 'This module is not enabled for your organization.'

    def has_permission(self, request, view):
        required_module = getattr(view, 'required_module', None)
        if not required_module:
            return True

        # Check tenant's enabled modules
        enabled_modules = getattr(request, 'enabled_modules', [])
        return required_module in enabled_modules
