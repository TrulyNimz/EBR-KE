"""
Celery tasks for async notification processing.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_notification_task(
    self,
    recipient_id: str,
    title: str,
    message: str,
    channel: str = 'in_app',
    template_code: str = None,
    context: dict = None,
    action_url: str = '',
    category: str = 'general',
    priority: str = 'normal',
    metadata: dict = None,
    related_type: str = None,
    related_id: str = None,
):
    """
    Async task to send a notification.
    """
    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from .models import NotificationTemplate
    from .services import NotificationService

    User = get_user_model()

    try:
        recipient = User.objects.get(id=recipient_id)
    except User.DoesNotExist:
        logger.error(f'Recipient not found: {recipient_id}')
        return

    # Get template if specified
    template = None
    if template_code:
        try:
            template = NotificationTemplate.objects.get(code=template_code, is_active=True)
        except NotificationTemplate.DoesNotExist:
            logger.warning(f'Template not found: {template_code}')

    # Get content type if specified
    content_type = None
    if related_type:
        try:
            app_label, model = related_type.lower().split('.')
            content_type = ContentType.objects.get(app_label=app_label, model=model)
        except (ValueError, ContentType.DoesNotExist):
            logger.warning(f'Invalid related_type: {related_type}')

    notification = NotificationService.send(
        recipient=recipient,
        title=title,
        message=message,
        channel=channel,
        template=template,
        context=context or {},
        action_url=action_url,
        category=category,
        priority=priority,
        metadata=metadata or {},
        content_type=content_type,
        object_id=related_id or '',
    )

    if notification:
        logger.info(f'Notification sent: {notification.id}')
        return str(notification.id)

    return None


@shared_task(bind=True, max_retries=3)
def send_batch_notifications_task(self, batch_id: str):
    """
    Process a notification batch.
    """
    from django.contrib.auth import get_user_model
    from .models import NotificationBatch
    from .services import NotificationService

    User = get_user_model()

    try:
        batch = NotificationBatch.objects.get(id=batch_id)
    except NotificationBatch.DoesNotExist:
        logger.error(f'Batch not found: {batch_id}')
        return

    if batch.status != NotificationBatch.Status.PENDING:
        logger.warning(f'Batch {batch_id} not in pending status')
        return

    # Mark as processing
    batch.status = NotificationBatch.Status.PROCESSING
    batch.started_at = timezone.now()
    batch.save(update_fields=['status', 'started_at'])

    # Get recipients based on filter
    recipient_filter = batch.recipient_filter
    queryset = User.objects.filter(is_active=True)

    if 'user_ids' in recipient_filter:
        queryset = queryset.filter(id__in=recipient_filter['user_ids'])
    if 'roles' in recipient_filter:
        queryset = queryset.filter(roles__code__in=recipient_filter['roles'])
    if 'tenant_id' in recipient_filter:
        queryset = queryset.filter(tenant_id=recipient_filter['tenant_id'])

    batch.recipient_count = queryset.count()
    batch.save(update_fields=['recipient_count'])

    # Send to each recipient
    template = batch.template
    context = batch.context
    sent_count = 0
    failed_count = 0

    for recipient in queryset.iterator():
        try:
            notification = NotificationService.send(
                recipient=recipient,
                title='',  # Will be rendered from template
                message='',
                channel=template.channel,
                template=template,
                context=context,
                category=template.category,
                priority=template.priority,
            )
            if notification and notification.status != 'failed':
                sent_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.exception(f'Failed to send to {recipient}: {e}')
            failed_count += 1

        # Update progress periodically
        if (sent_count + failed_count) % 100 == 0:
            batch.sent_count = sent_count
            batch.failed_count = failed_count
            batch.save(update_fields=['sent_count', 'failed_count'])

    # Mark as completed
    batch.status = NotificationBatch.Status.COMPLETED
    batch.sent_count = sent_count
    batch.failed_count = failed_count
    batch.completed_at = timezone.now()
    batch.save(update_fields=['status', 'sent_count', 'failed_count', 'completed_at'])

    logger.info(f'Batch {batch_id} completed: {sent_count} sent, {failed_count} failed')


@shared_task
def retry_failed_notifications_task():
    """
    Retry failed notifications that haven't exceeded max retries.
    """
    from .models import Notification
    from .services import NotificationService

    max_retries = 3
    failed = Notification.objects.filter(
        status=Notification.Status.FAILED,
        retry_count__lt=max_retries,
        created_at__gte=timezone.now() - timezone.timedelta(hours=24)
    )[:100]

    for notification in failed:
        try:
            # Re-send based on channel
            if notification.channel == 'email':
                from .services import EmailService
                EmailService.send(
                    recipient=notification.recipient.email,
                    subject=notification.title,
                    body=notification.message,
                    html_body=notification.html_content,
                )
            elif notification.channel == 'push':
                from .services import PushNotificationService
                PushNotificationService.send_to_user(
                    user=notification.recipient,
                    title=notification.title,
                    body=notification.message,
                    data=notification.metadata,
                    action_url=notification.action_url,
                )

            notification.status = Notification.Status.SENT
            notification.sent_at = timezone.now()
            notification.error_message = ''

        except Exception as e:
            notification.retry_count += 1
            notification.error_message = str(e)

        notification.save()


@shared_task
def send_email_digest_task():
    """
    Send email digests to users who have enabled them.
    """
    from django.contrib.auth import get_user_model
    from .models import Notification, UserNotificationPreference
    from .services import EmailService

    User = get_user_model()

    # Get users with daily digest enabled
    prefs = UserNotificationPreference.objects.filter(
        email_digest_enabled=True,
        email_digest_frequency='daily'
    ).select_related('user')

    cutoff = timezone.now() - timezone.timedelta(hours=24)

    for pref in prefs:
        user = pref.user

        # Get unread in-app notifications from last 24 hours
        notifications = Notification.objects.filter(
            recipient=user,
            channel='in_app',
            status__in=['sent', 'delivered'],
            created_at__gte=cutoff
        ).order_by('-created_at')[:20]

        if not notifications:
            continue

        # Build digest email
        subject = f'Your Daily Notification Digest - {notifications.count()} updates'
        body_lines = ['Here are your notifications from the past 24 hours:\n']

        for notif in notifications:
            body_lines.append(f'• {notif.title}')
            body_lines.append(f'  {notif.message[:100]}...\n')

        body = '\n'.join(body_lines)

        try:
            EmailService.send(
                recipient=user.email,
                subject=subject,
                body=body,
            )
            logger.info(f'Sent digest to {user.email}')
        except Exception as e:
            logger.exception(f'Failed to send digest to {user.email}: {e}')


@shared_task
def cleanup_old_notifications_task():
    """
    Clean up old notifications based on retention policy.
    """
    from .models import Notification

    # Delete read notifications older than 90 days
    cutoff_read = timezone.now() - timezone.timedelta(days=90)
    deleted_read, _ = Notification.objects.filter(
        status=Notification.Status.READ,
        read_at__lt=cutoff_read
    ).delete()

    # Delete all notifications older than 1 year
    cutoff_all = timezone.now() - timezone.timedelta(days=365)
    deleted_old, _ = Notification.objects.filter(
        created_at__lt=cutoff_all
    ).delete()

    logger.info(f'Cleaned up {deleted_read} read and {deleted_old} old notifications')


@shared_task
def send_workflow_notification_task(
    workflow_instance_id: str,
    event_type: str,
    actor_id: str = None,
):
    """
    Send notifications for workflow events.
    """
    from django.contrib.auth import get_user_model
    from apps.workflow.models import WorkflowInstance, ApprovalRequest
    from .models import NotificationTemplate

    User = get_user_model()

    try:
        instance = WorkflowInstance.objects.select_related(
            'workflow', 'current_state', 'started_by'
        ).get(id=workflow_instance_id)
    except WorkflowInstance.DoesNotExist:
        logger.error(f'Workflow instance not found: {workflow_instance_id}')
        return

    template_map = {
        'state_changed': 'workflow_state_changed',
        'approval_required': 'workflow_approval_required',
        'approved': 'workflow_approved',
        'rejected': 'workflow_rejected',
        'completed': 'workflow_completed',
    }

    template_code = template_map.get(event_type)
    if not template_code:
        logger.warning(f'Unknown workflow event type: {event_type}')
        return

    try:
        template = NotificationTemplate.objects.get(code=template_code, is_active=True)
    except NotificationTemplate.DoesNotExist:
        logger.warning(f'Template not found: {template_code}')
        return

    context = {
        'workflow_name': instance.workflow.name,
        'record_id': instance.record_id,
        'current_state': instance.current_state.name if instance.current_state else '',
        'started_by': instance.started_by.full_name if instance.started_by else '',
    }

    # Determine recipients based on event type
    recipients = []

    if event_type == 'approval_required':
        # Notify approvers
        pending_approvals = ApprovalRequest.objects.filter(
            instance=instance,
            status='pending'
        ).select_related('approval_rule')

        for approval in pending_approvals:
            # Get users who can approve
            if approval.approval_rule.approver_users.exists():
                recipients.extend(approval.approval_rule.approver_users.all())

            if approval.approval_rule.approver_roles:
                role_users = User.objects.filter(
                    roles__code__in=approval.approval_rule.approver_roles,
                    is_active=True
                )
                recipients.extend(role_users)

    elif event_type in ['approved', 'rejected', 'completed']:
        # Notify the workflow initiator
        if instance.started_by:
            recipients.append(instance.started_by)

    elif event_type == 'state_changed':
        # Notify the workflow initiator
        if instance.started_by:
            recipients.append(instance.started_by)

    # Send notifications
    from .services import NotificationService
    for recipient in set(recipients):  # Deduplicate
        NotificationService.send(
            recipient=recipient,
            title='',
            message='',
            channel='in_app',
            template=template,
            context=context,
            category='workflow',
            action_url=f'/workflows/instances/{instance.id}',
        )

    logger.info(f'Sent {len(recipients)} workflow notifications for {event_type}')
