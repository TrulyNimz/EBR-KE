"""
Notification delivery services.

Handles sending notifications via various channels:
- In-app (database)
- Email (SMTP/SendGrid)
- Push (Firebase Cloud Messaging)
- SMS (Africa's Talking / Twilio)
"""
import logging
from typing import Optional, List, Dict, Any
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Main notification service that coordinates delivery across channels.
    """

    @classmethod
    def send(
        cls,
        recipient,
        title: str,
        message: str,
        channel: str = 'in_app',
        template=None,
        context: Dict[str, Any] = None,
        action_url: str = '',
        category: str = 'general',
        priority: str = 'normal',
        metadata: Dict[str, Any] = None,
        content_type=None,
        object_id: str = '',
    ):
        """
        Send a notification to a single recipient.

        Returns the created Notification instance.
        """
        from .models import Notification, UserNotificationPreference

        # Check user preferences
        try:
            prefs = recipient.notification_preferences
            if not prefs.is_channel_enabled(channel, category):
                logger.info(f'Notification blocked by user preferences: {recipient} / {channel}')
                return None
            if template and not prefs.is_template_enabled(template.code):
                logger.info(f'Template blocked by user preferences: {recipient} / {template.code}')
                return None
        except UserNotificationPreference.DoesNotExist:
            pass  # No preferences set, send anyway

        # Render template if provided
        if template and context:
            rendered = template.render(context)
            title = rendered['subject'] or title
            message = rendered['body']
            html_content = rendered['html'] or ''
        else:
            html_content = ''

        # Create notification record
        notification = Notification.objects.create(
            recipient=recipient,
            template=template,
            channel=channel,
            title=title,
            message=message,
            html_content=html_content,
            category=category,
            priority=priority,
            action_url=action_url,
            content_type=content_type,
            object_id=object_id,
            metadata=metadata or {},
            tenant_id=getattr(recipient, 'tenant_id', ''),
        )

        # Send via appropriate channel
        try:
            if channel == 'in_app':
                # Already saved to DB, just mark as sent
                notification.status = Notification.Status.SENT
                notification.sent_at = timezone.now()
                notification.save(update_fields=['status', 'sent_at'])

            elif channel == 'email':
                EmailService.send(
                    recipient=recipient.email,
                    subject=title,
                    body=message,
                    html_body=html_content,
                )
                notification.status = Notification.Status.SENT
                notification.sent_at = timezone.now()
                notification.save(update_fields=['status', 'sent_at'])

            elif channel == 'push':
                PushNotificationService.send_to_user(
                    user=recipient,
                    title=title,
                    body=message,
                    data=metadata or {},
                    action_url=action_url,
                )
                notification.status = Notification.Status.SENT
                notification.sent_at = timezone.now()
                notification.save(update_fields=['status', 'sent_at'])

            elif channel == 'sms':
                # Get phone from user profile
                phone = getattr(recipient, 'phone', None)
                if phone:
                    SMSService.send(phone=phone, message=message)
                    notification.status = Notification.Status.SENT
                    notification.sent_at = timezone.now()
                    notification.save(update_fields=['status', 'sent_at'])
                else:
                    notification.status = Notification.Status.FAILED
                    notification.error_message = 'No phone number available'
                    notification.save(update_fields=['status', 'error_message'])

        except Exception as e:
            logger.exception(f'Failed to send notification: {e}')
            notification.status = Notification.Status.FAILED
            notification.error_message = str(e)
            notification.retry_count += 1
            notification.save(update_fields=['status', 'error_message', 'retry_count'])

        return notification

    @classmethod
    def send_bulk(
        cls,
        recipients: List,
        title: str,
        message: str,
        channel: str = 'in_app',
        template=None,
        context: Dict[str, Any] = None,
        **kwargs
    ) -> List:
        """Send notification to multiple recipients."""
        notifications = []
        for recipient in recipients:
            notif = cls.send(
                recipient=recipient,
                title=title,
                message=message,
                channel=channel,
                template=template,
                context=context,
                **kwargs
            )
            if notif:
                notifications.append(notif)
        return notifications


class EmailService:
    """
    Email sending service.
    """

    @classmethod
    def send(
        cls,
        recipient: str,
        subject: str,
        body: str,
        html_body: str = '',
        from_email: str = None,
        attachments: List = None,
    ) -> bool:
        """
        Send an email.

        Returns True if sent successfully.
        """
        try:
            from_email = from_email or settings.DEFAULT_FROM_EMAIL

            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[recipient],
            )

            if html_body:
                email.attach_alternative(html_body, 'text/html')

            if attachments:
                for attachment in attachments:
                    email.attach(*attachment)

            email.send(fail_silently=False)
            logger.info(f'Email sent to {recipient}: {subject}')
            return True

        except Exception as e:
            logger.exception(f'Failed to send email to {recipient}: {e}')
            raise


class PushNotificationService:
    """
    Push notification service using Firebase Cloud Messaging.
    """

    _initialized = False
    _firebase_app = None

    @classmethod
    def _initialize(cls):
        """Initialize Firebase Admin SDK."""
        if cls._initialized:
            return

        try:
            import firebase_admin
            from firebase_admin import credentials

            # Initialize with service account
            cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
            if cred_path:
                cred = credentials.Certificate(cred_path)
                cls._firebase_app = firebase_admin.initialize_app(cred)
                cls._initialized = True
                logger.info('Firebase Admin SDK initialized')
            else:
                logger.warning('Firebase credentials not configured')

        except Exception as e:
            logger.exception(f'Failed to initialize Firebase: {e}')

    @classmethod
    def send_to_user(
        cls,
        user,
        title: str,
        body: str,
        data: Dict[str, Any] = None,
        action_url: str = '',
    ) -> int:
        """
        Send push notification to all user's devices.

        Returns number of successful sends.
        """
        from .models import DeviceToken

        tokens = DeviceToken.objects.filter(
            user=user,
            is_active=True
        ).values_list('token', flat=True)

        if not tokens:
            logger.info(f'No active device tokens for user {user}')
            return 0

        return cls.send_to_tokens(
            tokens=list(tokens),
            title=title,
            body=body,
            data=data,
            action_url=action_url,
        )

    @classmethod
    def send_to_tokens(
        cls,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, Any] = None,
        action_url: str = '',
    ) -> int:
        """
        Send push notification to specific device tokens.

        Returns number of successful sends.
        """
        cls._initialize()

        if not cls._initialized:
            logger.warning('Firebase not initialized, skipping push')
            return 0

        try:
            from firebase_admin import messaging

            # Prepare data payload
            payload_data = data or {}
            if action_url:
                payload_data['action_url'] = action_url

            # Convert all values to strings (FCM requirement)
            payload_data = {k: str(v) for k, v in payload_data.items()}

            # Create message
            message = messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=payload_data,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#1976D2',
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=1,
                            sound='default',
                        ),
                    ),
                ),
            )

            # Send
            response = messaging.send_multicast(message)
            logger.info(
                f'Push sent: {response.success_count} success, '
                f'{response.failure_count} failed'
            )

            # Handle failed tokens (mark as inactive)
            if response.failure_count > 0:
                cls._handle_failed_tokens(tokens, response.responses)

            return response.success_count

        except Exception as e:
            logger.exception(f'Failed to send push notification: {e}')
            raise

    @classmethod
    def _handle_failed_tokens(cls, tokens: List[str], responses: List):
        """Mark failed tokens as inactive."""
        from firebase_admin import messaging
        from .models import DeviceToken

        failed_tokens = []
        for idx, resp in enumerate(responses):
            if not resp.success:
                error = resp.exception
                # Check for unrecoverable errors
                if isinstance(error, (
                    messaging.UnregisteredError,
                    messaging.SenderIdMismatchError,
                )):
                    failed_tokens.append(tokens[idx])

        if failed_tokens:
            DeviceToken.objects.filter(token__in=failed_tokens).update(is_active=False)
            logger.info(f'Marked {len(failed_tokens)} tokens as inactive')


class SMSService:
    """
    SMS sending service.

    Supports Africa's Talking for Kenya and Twilio as fallback.
    """

    @classmethod
    def send(cls, phone: str, message: str) -> bool:
        """
        Send an SMS message.

        Returns True if sent successfully.
        """
        # Try Africa's Talking first (for Kenya)
        if phone.startswith('+254') or phone.startswith('254'):
            return cls._send_africastalking(phone, message)

        # Fallback to Twilio
        return cls._send_twilio(phone, message)

    @classmethod
    def _send_africastalking(cls, phone: str, message: str) -> bool:
        """Send SMS via Africa's Talking."""
        try:
            import africastalking

            username = getattr(settings, 'AFRICASTALKING_USERNAME', None)
            api_key = getattr(settings, 'AFRICASTALKING_API_KEY', None)

            if not username or not api_key:
                logger.warning('Africa\'s Talking not configured')
                return False

            africastalking.initialize(username, api_key)
            sms = africastalking.SMS

            response = sms.send(message, [phone])
            logger.info(f'SMS sent via AT to {phone}: {response}')
            return True

        except Exception as e:
            logger.exception(f'Failed to send SMS via AT: {e}')
            raise

    @classmethod
    def _send_twilio(cls, phone: str, message: str) -> bool:
        """Send SMS via Twilio."""
        try:
            from twilio.rest import Client

            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            from_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

            if not all([account_sid, auth_token, from_phone]):
                logger.warning('Twilio not configured')
                return False

            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=message,
                from_=from_phone,
                to=phone,
            )
            logger.info(f'SMS sent via Twilio to {phone}: {message.sid}')
            return True

        except Exception as e:
            logger.exception(f'Failed to send SMS via Twilio: {e}')
            raise
