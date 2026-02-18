"""
Notification serializers.
"""
from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import (
    Notification,
    NotificationTemplate,
    UserNotificationPreference,
    DeviceToken,
    NotificationBatch,
)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Notification template serializer."""

    class Meta:
        model = NotificationTemplate
        fields = [
            'id',
            'code',
            'name',
            'description',
            'channel',
            'subject_template',
            'body_template',
            'html_template',
            'category',
            'priority',
            'is_active',
            'allow_user_disable',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer for reading."""

    template_code = serializers.CharField(
        source='template.code',
        read_only=True,
        allow_null=True
    )
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'channel',
            'title',
            'message',
            'category',
            'priority',
            'action_url',
            'status',
            'template_code',
            'content_type',
            'object_id',
            'metadata',
            'created_at',
            'sent_at',
            'read_at',
            'time_ago',
        ]
        read_only_fields = fields

    def get_time_ago(self, obj):
        """Get human-readable time ago string."""
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        diff = now - obj.created_at

        if diff < timedelta(minutes=1):
            return 'Just now'
        elif diff < timedelta(hours=1):
            mins = int(diff.total_seconds() / 60)
            return f'{mins}m ago'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours}h ago'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days}d ago'
        else:
            return obj.created_at.strftime('%b %d')


class NotificationCreateSerializer(serializers.Serializer):
    """Serializer for creating notifications."""

    recipient_id = serializers.UUIDField(required=False)
    recipient_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    template_code = serializers.CharField(required=False)
    channel = serializers.ChoiceField(
        choices=NotificationTemplate.Channel.choices,
        default='in_app'
    )
    title = serializers.CharField(max_length=255, required=False)
    message = serializers.CharField(required=False)
    category = serializers.CharField(max_length=50, default='general')
    priority = serializers.CharField(max_length=20, default='normal')
    action_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    context = serializers.JSONField(default=dict)
    metadata = serializers.JSONField(default=dict)

    # Related object
    related_type = serializers.CharField(required=False, allow_blank=True)
    related_id = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Must have recipient(s)
        if not attrs.get('recipient_id') and not attrs.get('recipient_ids'):
            raise serializers.ValidationError(
                'Either recipient_id or recipient_ids is required.'
            )

        # Must have template_code OR (title AND message)
        if not attrs.get('template_code'):
            if not attrs.get('title') or not attrs.get('message'):
                raise serializers.ValidationError(
                    'Either template_code or both title and message are required.'
                )

        # Validate template exists
        if attrs.get('template_code'):
            try:
                template = NotificationTemplate.objects.get(
                    code=attrs['template_code'],
                    is_active=True
                )
                attrs['template'] = template
            except NotificationTemplate.DoesNotExist:
                raise serializers.ValidationError({
                    'template_code': f"Template '{attrs['template_code']}' not found or inactive."
                })

        # Validate related object type
        if attrs.get('related_type'):
            try:
                app_label, model = attrs['related_type'].lower().split('.')
                content_type = ContentType.objects.get(app_label=app_label, model=model)
                attrs['content_type'] = content_type
            except (ValueError, ContentType.DoesNotExist):
                raise serializers.ValidationError({
                    'related_type': f"Invalid type: {attrs['related_type']}"
                })

        return attrs


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    """User notification preferences serializer."""

    class Meta:
        model = UserNotificationPreference
        fields = [
            'email_enabled',
            'push_enabled',
            'sms_enabled',
            'in_app_enabled',
            'quiet_hours_enabled',
            'quiet_hours_start',
            'quiet_hours_end',
            'category_settings',
            'disabled_templates',
            'email_digest_enabled',
            'email_digest_frequency',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Device token serializer."""

    class Meta:
        model = DeviceToken
        fields = [
            'id',
            'token',
            'platform',
            'device_id',
            'device_name',
            'app_version',
            'is_active',
            'last_used_at',
            'created_at',
        ]
        read_only_fields = ['id', 'last_used_at', 'created_at']


class DeviceTokenRegisterSerializer(serializers.Serializer):
    """Serializer for registering device tokens."""

    token = serializers.CharField(max_length=500)
    platform = serializers.ChoiceField(choices=DeviceToken.Platform.choices)
    device_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    device_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    app_version = serializers.CharField(max_length=50, required=False, allow_blank=True)


class NotificationBatchSerializer(serializers.ModelSerializer):
    """Notification batch serializer."""

    template_code = serializers.CharField(source='template.code', read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True,
        allow_null=True
    )
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = NotificationBatch
        fields = [
            'id',
            'template',
            'template_code',
            'context',
            'recipient_filter',
            'recipient_count',
            'status',
            'sent_count',
            'failed_count',
            'progress_percentage',
            'created_at',
            'started_at',
            'completed_at',
            'created_by',
            'created_by_name',
        ]
        read_only_fields = [
            'id', 'recipient_count', 'status', 'sent_count', 'failed_count',
            'created_at', 'started_at', 'completed_at', 'created_by',
        ]

    def get_progress_percentage(self, obj):
        if obj.recipient_count == 0:
            return 0
        return int(((obj.sent_count + obj.failed_count) / obj.recipient_count) * 100)


class MarkNotificationsReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read."""

    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    mark_all = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if not attrs.get('notification_ids') and not attrs.get('mark_all'):
            raise serializers.ValidationError(
                'Either notification_ids or mark_all=true is required.'
            )
        return attrs
