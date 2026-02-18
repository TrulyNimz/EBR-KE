"""
Notification models.

Supports in-app notifications, email, SMS, and push notifications.
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.core.models import AuditableModel


class NotificationTemplate(models.Model):
    """
    Reusable notification templates.
    """

    class Channel(models.TextChoices):
        IN_APP = 'in_app', 'In-App'
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        PUSH = 'push', 'Push Notification'

    # Identification
    code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Channel
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.IN_APP
    )

    # Content templates (support variable substitution with {{variable}})
    subject_template = models.CharField(
        max_length=255,
        blank=True,
        help_text='Subject line for email/push. Supports {{variables}}'
    )
    body_template = models.TextField(
        help_text='Notification body. Supports {{variables}} and markdown'
    )
    html_template = models.TextField(
        blank=True,
        help_text='HTML template for email (optional)'
    )

    # Categorization
    category = models.CharField(
        max_length=50,
        default='general',
        help_text='e.g., workflow, alert, reminder, system'
    )
    priority = models.CharField(
        max_length=20,
        default='normal',
        help_text='low, normal, high, urgent'
    )

    # Settings
    is_active = models.BooleanField(default=True)
    allow_user_disable = models.BooleanField(
        default=True,
        help_text='Whether users can disable this notification type'
    )

    # Tenant (empty for system-wide templates)
    tenant_id = models.CharField(max_length=255, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_templates'
        ordering = ['category', 'name']

    def __str__(self):
        return f'{self.code} ({self.channel})'

    def render(self, context: dict) -> dict:
        """Render template with context variables."""
        import re

        def substitute(template, ctx):
            if not template:
                return template
            for key, value in ctx.items():
                template = template.replace(f'{{{{{key}}}}}', str(value))
            # Remove any remaining unsubstituted variables
            template = re.sub(r'\{\{[^}]+\}\}', '', template)
            return template

        return {
            'subject': substitute(self.subject_template, context),
            'body': substitute(self.body_template, context),
            'html': substitute(self.html_template, context) if self.html_template else None,
        }


class Notification(models.Model):
    """
    Individual notification instance.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        READ = 'read', 'Read'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Recipient
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Template (optional - can send ad-hoc notifications)
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )

    # Channel
    channel = models.CharField(
        max_length=20,
        choices=NotificationTemplate.Channel.choices,
        default=NotificationTemplate.Channel.IN_APP
    )

    # Content
    title = models.CharField(max_length=255)
    message = models.TextField()
    html_content = models.TextField(blank=True)

    # Categorization
    category = models.CharField(max_length=50, default='general')
    priority = models.CharField(max_length=20, default='normal')

    # Related object (optional - for linking to specific records)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.CharField(max_length=255, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    # Action URL (for navigation)
    action_url = models.CharField(
        max_length=500,
        blank=True,
        help_text='URL to navigate to when notification is clicked'
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    metadata = models.JSONField(
        default=dict,
        help_text='Additional data for the notification'
    )

    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status', '-created_at']),
            models.Index(fields=['tenant_id', 'recipient', '-created_at']),
        ]

    def __str__(self):
        return f'{self.title} -> {self.recipient}'

    def mark_as_read(self):
        """Mark notification as read."""
        from django.utils import timezone
        if self.status != self.Status.READ:
            self.status = self.Status.READ
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])


class UserNotificationPreference(models.Model):
    """
    User preferences for notifications.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Global settings
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)

    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    # Category-specific settings (JSON: {category: {channel: enabled}})
    category_settings = models.JSONField(
        default=dict,
        help_text='Category-specific notification settings'
    )

    # Disabled templates (list of template codes)
    disabled_templates = models.JSONField(
        default=list,
        help_text='List of disabled notification template codes'
    )

    # Digest settings
    email_digest_enabled = models.BooleanField(default=False)
    email_digest_frequency = models.CharField(
        max_length=20,
        default='daily',
        help_text='immediate, daily, weekly'
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_notification_preferences'

    def __str__(self):
        return f'Preferences for {self.user}'

    def is_channel_enabled(self, channel: str, category: str = None) -> bool:
        """Check if a channel is enabled for the user."""
        # Check global setting first
        channel_map = {
            'email': self.email_enabled,
            'push': self.push_enabled,
            'sms': self.sms_enabled,
            'in_app': self.in_app_enabled,
        }

        if not channel_map.get(channel, True):
            return False

        # Check category-specific setting
        if category and category in self.category_settings:
            cat_settings = self.category_settings[category]
            if channel in cat_settings:
                return cat_settings[channel]

        return True

    def is_template_enabled(self, template_code: str) -> bool:
        """Check if a template is enabled for the user."""
        return template_code not in self.disabled_templates


class DeviceToken(models.Model):
    """
    Push notification device tokens.
    """

    class Platform(models.TextChoices):
        IOS = 'ios', 'iOS'
        ANDROID = 'android', 'Android'
        WEB = 'web', 'Web'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens'
    )

    # Token
    token = models.CharField(max_length=500, unique=True)
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices
    )

    # Device info
    device_id = models.CharField(max_length=255, blank=True)
    device_name = models.CharField(max_length=255, blank=True)
    app_version = models.CharField(max_length=50, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'device_tokens'
        ordering = ['-last_used_at']

    def __str__(self):
        return f'{self.user} - {self.platform} ({self.device_name or "Unknown"})'


class NotificationBatch(models.Model):
    """
    Batch notification for sending to multiple users.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Template
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.PROTECT,
        related_name='batches'
    )

    # Context for template rendering
    context = models.JSONField(default=dict)

    # Recipients (can be user IDs or filter criteria)
    recipient_filter = models.JSONField(
        default=dict,
        help_text='Filter criteria for recipients'
    )
    recipient_count = models.PositiveIntegerField(default=0)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Progress
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Created by
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notification_batches'
    )

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'notification_batches'
        ordering = ['-created_at']

    def __str__(self):
        return f'Batch {self.id} - {self.template.code}'
