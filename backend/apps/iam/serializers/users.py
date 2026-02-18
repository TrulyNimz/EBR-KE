"""
User serializers for the EBR Platform.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import timedelta

from apps.iam.models import User, UserRole


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model (read operations).
    """
    full_name = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'employee_id',
            'first_name',
            'last_name',
            'full_name',
            'title',
            'department',
            'phone',
            'is_active',
            'is_locked',
            'mfa_enabled',
            'digital_signature_enabled',
            'last_login',
            'created_at',
            'roles',
            'permissions',
        ]
        read_only_fields = [
            'id',
            'is_locked',
            'last_login',
            'created_at',
        ]

    def get_roles(self, obj):
        """Get active roles for the user."""
        now = timezone.now()
        return list(
            obj.user_roles.filter(
                valid_from__lte=now
            ).filter(
                models.Q(valid_until__isnull=True) |
                models.Q(valid_until__gt=now)
            ).values_list('role__code', flat=True)
        )

    def get_permissions(self, obj):
        """Get all permissions for the user."""
        return list(obj.get_all_permissions_set())


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email',
            'employee_id',
            'first_name',
            'last_name',
            'title',
            'department',
            'phone',
            'password',
            'confirm_password',
        ]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return attrs

    def create(self, validated_data):
        # Set password expiration (90 days from now)
        validated_data['password_expires_at'] = timezone.now() + timedelta(days=90)
        validated_data['password_changed_at'] = timezone.now()
        validated_data['must_change_password'] = True

        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating users.
    """

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'title',
            'department',
            'phone',
            'is_active',
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user's own profile.
    """
    full_name = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    tenant = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'employee_id',
            'first_name',
            'last_name',
            'full_name',
            'title',
            'department',
            'phone',
            'mfa_enabled',
            'digital_signature_enabled',
            'must_change_password',
            'password_expires_at',
            'last_login',
            'roles',
            'permissions',
            'tenant',
        ]
        read_only_fields = fields

    def get_roles(self, obj):
        now = timezone.now()
        return list(
            obj.user_roles.filter(
                valid_from__lte=now
            ).filter(
                models.Q(valid_until__isnull=True) |
                models.Q(valid_until__gt=now)
            ).values_list('role__code', flat=True)
        )

    def get_permissions(self, obj):
        return list(obj.get_all_permissions_set())

    def get_tenant(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'tenant'):
            return {
                'id': str(request.tenant.id),
                'name': request.tenant.name,
                'industry': request.tenant.industry,
                'enabled_modules': request.tenant.enabled_modules,
            }
        return None
