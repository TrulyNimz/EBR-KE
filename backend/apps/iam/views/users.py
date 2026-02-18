"""
User views for the EBR Platform.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.iam.models import User
from apps.iam.serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserProfileSerializer,
)
from apps.iam.permissions import RBACPermission


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User management.

    GET /api/v1/users/ - List users
    POST /api/v1/users/ - Create user
    GET /api/v1/users/{id}/ - Get user
    PATCH /api/v1/users/{id}/ - Update user
    DELETE /api/v1/users/{id}/ - Deactivate user
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'iam.user.read'
    filterset_fields = ['is_active', 'department']
    search_fields = ['email', 'first_name', 'last_name', 'employee_id']
    ordering_fields = ['created_at', 'email', 'last_name']
    ordering = ['last_name', 'first_name']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'iam.user.create'
        elif self.action in ['update', 'partial_update']:
            self.required_permission = 'iam.user.update'
        elif self.action == 'destroy':
            self.required_permission = 'iam.user.delete'
        return super().get_permissions()

    def perform_destroy(self, instance):
        """Soft delete - deactivate user instead of deleting."""
        instance.is_active = False
        instance.deactivated_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """Lock a user account."""
        self.required_permission = 'iam.user.lock'
        user = self.get_object()
        reason = request.data.get('reason', 'Locked by administrator')
        user.lock_account(reason=reason)
        return Response({'message': f'User {user.email} has been locked.'})

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """Unlock a user account."""
        self.required_permission = 'iam.user.unlock'
        user = self.get_object()
        user.unlock_account()
        return Response({'message': f'User {user.email} has been unlocked.'})

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Force password reset for a user."""
        self.required_permission = 'iam.user.reset_password'
        user = self.get_object()
        user.must_change_password = True
        user.save(update_fields=['must_change_password'])
        return Response({'message': f'Password reset required for {user.email}.'})


class CurrentUserView(APIView):
    """
    Get or update current authenticated user's profile.

    GET /api/v1/users/me/
    PATCH /api/v1/users/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        # Users can only update certain fields
        allowed_fields = ['first_name', 'last_name', 'phone']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        for field, value in update_data.items():
            setattr(request.user, field, value)
        request.user.save(update_fields=list(update_data.keys()))

        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)
