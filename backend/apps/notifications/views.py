"""
Notification views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    Notification,
    NotificationTemplate,
    UserNotificationPreference,
    DeviceToken,
    NotificationBatch,
)
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationTemplateSerializer,
    UserNotificationPreferenceSerializer,
    DeviceTokenSerializer,
    DeviceTokenRegisterSerializer,
    NotificationBatchSerializer,
    MarkNotificationsReadSerializer,
)
from .services import NotificationService
from .tasks import send_notification_task, send_batch_notifications_task
from apps.iam.permissions import RBACPermission


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user notifications.

    GET  /api/v1/notifications/              - List user's notifications
    GET  /api/v1/notifications/{id}/         - Get notification detail
    POST /api/v1/notifications/mark-read/    - Mark notifications as read
    GET  /api/v1/notifications/unread-count/ - Get unread count
    GET  /api/v1/notifications/summary/      - Get notification summary
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'channel', 'category', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get notifications for current user."""
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('template')

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        """Mark notifications as read."""
        serializer = MarkNotificationsReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        queryset = self.get_queryset().filter(
            status__in=[Notification.Status.SENT, Notification.Status.DELIVERED]
        )

        if serializer.validated_data.get('mark_all'):
            count = queryset.update(
                status=Notification.Status.READ,
                read_at=timezone.now()
            )
        else:
            notification_ids = serializer.validated_data.get('notification_ids', [])
            count = queryset.filter(id__in=notification_ids).update(
                status=Notification.Status.READ,
                read_at=timezone.now()
            )

        return Response({
            'message': f'{count} notifications marked as read',
            'count': count
        })

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """Get count of unread notifications."""
        count = self.get_queryset().filter(
            status__in=[Notification.Status.SENT, Notification.Status.DELIVERED]
        ).count()

        return Response({'unread_count': count})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get notification summary by category."""
        queryset = self.get_queryset()

        # Counts by status
        status_counts = queryset.values('status').annotate(count=Count('id'))

        # Unread by category
        unread_by_category = queryset.filter(
            status__in=[Notification.Status.SENT, Notification.Status.DELIVERED]
        ).values('category').annotate(count=Count('id'))

        # Recent high priority
        high_priority = queryset.filter(
            priority__in=['high', 'urgent'],
            status__in=[Notification.Status.SENT, Notification.Status.DELIVERED]
        ).count()

        return Response({
            'status_counts': {item['status']: item['count'] for item in status_counts},
            'unread_by_category': {item['category']: item['count'] for item in unread_by_category},
            'high_priority_unread': high_priority,
            'total': queryset.count(),
        })

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mark a single notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response(NotificationSerializer(notification).data)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notification templates (admin only).
    """

    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'notifications.template.read'
    filterset_fields = ['channel', 'category', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['category', 'name']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return NotificationTemplate.objects.filter(
            Q(tenant_id=tenant_id) | Q(tenant_id='')
        )

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.required_permission = 'notifications.template.manage'
        return super().get_permissions()

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', '')
        serializer.save(tenant_id=tenant_id)

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Preview a template with sample data."""
        template = self.get_object()
        context = request.data.get('context', {})
        rendered = template.render(context)
        return Response(rendered)


class UserNotificationPreferenceView(APIView):
    """
    View for managing user notification preferences.

    GET  /api/v1/notifications/preferences/  - Get preferences
    PUT  /api/v1/notifications/preferences/  - Update preferences
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's notification preferences."""
        prefs, _ = UserNotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = UserNotificationPreferenceSerializer(prefs)
        return Response(serializer.data)

    def put(self, request):
        """Update user's notification preferences."""
        prefs, _ = UserNotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = UserNotificationPreferenceSerializer(prefs, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        """Partially update preferences."""
        prefs, _ = UserNotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = UserNotificationPreferenceSerializer(
            prefs, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing device tokens for push notifications.
    """

    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new device token."""
        serializer = DeviceTokenRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Update existing or create new
        token, created = DeviceToken.objects.update_or_create(
            token=data['token'],
            defaults={
                'user': request.user,
                'platform': data['platform'],
                'device_id': data.get('device_id', ''),
                'device_name': data.get('device_name', ''),
                'app_version': data.get('app_version', ''),
                'is_active': True,
            }
        )

        return Response(
            DeviceTokenSerializer(token).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def unregister(self, request):
        """Unregister a device token."""
        token_value = request.data.get('token')
        if not token_value:
            return Response(
                {'error': 'Token required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted, _ = DeviceToken.objects.filter(
            user=request.user,
            token=token_value
        ).delete()

        if deleted:
            return Response({'message': 'Token unregistered'})
        return Response(
            {'error': 'Token not found'},
            status=status.HTTP_404_NOT_FOUND
        )


class SendNotificationView(APIView):
    """
    View for sending notifications (admin/system use).

    POST /api/v1/notifications/send/  - Send notification
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'notifications.send'

    def post(self, request):
        """Send a notification."""
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Get recipient(s)
        from django.contrib.auth import get_user_model
        User = get_user_model()

        if data.get('recipient_id'):
            recipient_ids = [str(data['recipient_id'])]
        else:
            recipient_ids = [str(rid) for rid in data.get('recipient_ids', [])]

        # Send async
        async_send = request.data.get('async', True)
        notifications = []

        for recipient_id in recipient_ids:
            if async_send:
                send_notification_task.delay(
                    recipient_id=recipient_id,
                    title=data.get('title', ''),
                    message=data.get('message', ''),
                    channel=data.get('channel', 'in_app'),
                    template_code=data.get('template_code'),
                    context=data.get('context', {}),
                    action_url=data.get('action_url', ''),
                    category=data.get('category', 'general'),
                    priority=data.get('priority', 'normal'),
                    metadata=data.get('metadata', {}),
                    related_type=data.get('related_type'),
                    related_id=data.get('related_id'),
                )
                notifications.append({'recipient_id': recipient_id, 'status': 'queued'})
            else:
                try:
                    recipient = User.objects.get(id=recipient_id)
                    notif = NotificationService.send(
                        recipient=recipient,
                        title=data.get('title', ''),
                        message=data.get('message', ''),
                        channel=data.get('channel', 'in_app'),
                        template=data.get('template'),
                        context=data.get('context', {}),
                        action_url=data.get('action_url', ''),
                        category=data.get('category', 'general'),
                        priority=data.get('priority', 'normal'),
                        metadata=data.get('metadata', {}),
                        content_type=data.get('content_type'),
                        object_id=data.get('related_id', ''),
                    )
                    notifications.append({
                        'recipient_id': recipient_id,
                        'notification_id': str(notif.id) if notif else None,
                        'status': notif.status if notif else 'blocked'
                    })
                except User.DoesNotExist:
                    notifications.append({
                        'recipient_id': recipient_id,
                        'status': 'user_not_found'
                    })

        return Response({
            'message': f'Notification(s) {"queued" if async_send else "sent"}',
            'notifications': notifications
        })


class NotificationBatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for batch notifications (admin only).
    """

    serializer_class = NotificationBatchSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'notifications.batch.read'
    filterset_fields = ['status', 'template']
    ordering = ['-created_at']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return NotificationBatch.objects.filter(
            tenant_id=tenant_id
        ).select_related('template', 'created_by')

    def get_permissions(self):
        if self.action in ['create', 'send']:
            self.required_permission = 'notifications.batch.create'
        return super().get_permissions()

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', '')
        serializer.save(
            created_by=self.request.user,
            tenant_id=tenant_id
        )

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Start sending a batch."""
        batch = self.get_object()

        if batch.status != NotificationBatch.Status.PENDING:
            return Response(
                {'error': f'Batch is not pending. Status: {batch.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        send_batch_notifications_task.delay(str(batch.id))

        return Response({
            'message': 'Batch processing started',
            'batch': NotificationBatchSerializer(batch).data
        })


class NotificationSSEView(APIView):
    """
    Server-Sent Events endpoint for real-time notifications.

    GET /api/v1/notifications/stream/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Stream notifications via SSE."""
        from django.http import StreamingHttpResponse
        import json
        import time

        def event_stream():
            last_id = None

            while True:
                # Check for new notifications
                queryset = Notification.objects.filter(
                    recipient=request.user,
                    status=Notification.Status.SENT
                ).order_by('-created_at')

                if last_id:
                    queryset = queryset.filter(created_at__gt=last_id)

                notifications = list(queryset[:10])

                if notifications:
                    last_id = notifications[0].created_at
                    data = NotificationSerializer(notifications, many=True).data
                    yield f"data: {json.dumps(data)}\n\n"

                # Also send heartbeat
                yield f": heartbeat\n\n"

                time.sleep(5)  # Check every 5 seconds

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
