"""
Role and Permission views for the EBR Platform.
"""
from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from apps.iam.models import Permission, Role, UserRole
from apps.iam.serializers import (
    PermissionSerializer,
    RoleSerializer,
    UserRoleSerializer,
)
from apps.iam.permissions import RBACPermission


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Permission model (read-only).

    GET /api/v1/permissions/ - List all permissions
    GET /api/v1/permissions/{id}/ - Get permission detail
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'iam.permission.read'
    filterset_fields = ['module', 'resource', 'action']
    search_fields = ['code', 'name', 'description']


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Role management.

    GET /api/v1/roles/ - List roles
    POST /api/v1/roles/ - Create role
    GET /api/v1/roles/{id}/ - Get role
    PATCH /api/v1/roles/{id}/ - Update role
    DELETE /api/v1/roles/{id}/ - Delete role
    """
    queryset = Role.objects.filter(is_active=True)
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'iam.role.read'
    filterset_fields = ['is_system_role']
    search_fields = ['name', 'code', 'description']

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'iam.role.create'
        elif self.action in ['update', 'partial_update']:
            self.required_permission = 'iam.role.update'
        elif self.action == 'destroy':
            self.required_permission = 'iam.role.delete'
        return super().get_permissions()

    def perform_destroy(self, instance):
        """Soft delete - deactivate role instead of deleting."""
        if instance.is_system_role:
            raise serializers.ValidationError('Cannot delete system roles.')
        instance.is_active = False
        instance.save()

    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Get all permissions for a role (including inherited)."""
        role = self.get_object()
        all_perms = role.get_all_permissions()
        serializer = PermissionSerializer(all_perms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_permission(self, request, pk=None):
        """Add a permission to a role."""
        self.required_permission = 'iam.role.update'
        role = self.get_object()
        permission_id = request.data.get('permission_id')

        try:
            permission = Permission.objects.get(id=permission_id)
            role.permissions.add(permission)
            return Response({'message': f'Permission {permission.code} added to {role.name}.'})
        except Permission.DoesNotExist:
            return Response(
                {'error': 'Permission not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def remove_permission(self, request, pk=None):
        """Remove a permission from a role."""
        self.required_permission = 'iam.role.update'
        role = self.get_object()
        permission_id = request.data.get('permission_id')

        try:
            permission = Permission.objects.get(id=permission_id)
            role.permissions.remove(permission)
            return Response({'message': f'Permission {permission.code} removed from {role.name}.'})
        except Permission.DoesNotExist:
            return Response(
                {'error': 'Permission not found.'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserRoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User-Role assignments.

    GET /api/v1/user-roles/ - List assignments
    POST /api/v1/user-roles/ - Create assignment
    GET /api/v1/user-roles/{id}/ - Get assignment
    DELETE /api/v1/user-roles/{id}/ - Remove assignment
    """
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'iam.user_role.read'
    filterset_fields = ['user', 'role', 'scope_type']

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'iam.user_role.create'
        elif self.action == 'destroy':
            self.required_permission = 'iam.user_role.delete'
        return super().get_permissions()
