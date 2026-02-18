"""
Role and Permission serializers for the EBR Platform.
"""
from rest_framework import serializers
from apps.iam.models import Permission, Role, UserRole


class PermissionSerializer(serializers.ModelSerializer):
    """
    Serializer for Permission model.
    """

    class Meta:
        model = Permission
        fields = [
            'id',
            'code',
            'name',
            'description',
            'module',
            'resource',
            'action',
            'is_system',
        ]
        read_only_fields = ['id', 'is_system']


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer for Role model.
    """
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    parent_role_name = serializers.CharField(
        source='parent_role.name',
        read_only=True
    )

    class Meta:
        model = Role
        fields = [
            'id',
            'name',
            'code',
            'description',
            'parent_role',
            'parent_role_name',
            'permissions',
            'permission_ids',
            'is_system_role',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_system_role', 'created_at', 'updated_at']

    def create(self, validated_data):
        permission_ids = validated_data.pop('permission_ids', [])
        role = Role.objects.create(**validated_data)

        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            for perm in permissions:
                role.permissions.add(perm)

        return role

    def update(self, instance, validated_data):
        permission_ids = validated_data.pop('permission_ids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if permission_ids is not None:
            instance.permissions.clear()
            permissions = Permission.objects.filter(id__in=permission_ids)
            for perm in permissions:
                instance.permissions.add(perm)

        return instance


class UserRoleSerializer(serializers.ModelSerializer):
    """
    Serializer for UserRole assignments.
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    assigned_by_name = serializers.CharField(
        source='assigned_by.full_name',
        read_only=True
    )

    class Meta:
        model = UserRole
        fields = [
            'id',
            'user',
            'user_email',
            'role',
            'role_name',
            'scope_type',
            'scope_id',
            'scope_name',
            'valid_from',
            'valid_until',
            'assigned_by',
            'assigned_by_name',
            'assigned_at',
            'reason',
        ]
        read_only_fields = [
            'id',
            'assigned_by',
            'assigned_at',
        ]

    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        return super().create(validated_data)
