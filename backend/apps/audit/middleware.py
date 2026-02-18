"""
Audit middleware for automatic action logging.

Captures request context and provides it to audit services
throughout the request lifecycle.
"""
import threading
import uuid

from django.utils.deprecation import MiddlewareMixin

# Thread-local storage for request context
_audit_context = threading.local()


def get_audit_context():
    """Get the current request's audit context."""
    return getattr(_audit_context, 'context', {})


def set_audit_context(**kwargs):
    """Set audit context values."""
    if not hasattr(_audit_context, 'context'):
        _audit_context.context = {}
    _audit_context.context.update(kwargs)


def clear_audit_context():
    """Clear the audit context."""
    _audit_context.context = {}


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to capture request context for audit logging.

    Stores user, IP, session, and tenant info in thread-local storage
    for access by audit signals and services throughout the request.
    """

    def process_request(self, request):
        """Store audit context for the current request."""
        # Generate unique request ID for correlation
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

        # Get client IP
        ip_address = self._get_client_ip(request)

        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Get tenant from request (set by tenant middleware)
        tenant_id = getattr(request, 'tenant_id', '')
        if not tenant_id and hasattr(request, 'tenant'):
            tenant_id = str(getattr(request.tenant, 'id', ''))

        # Store context
        set_audit_context(
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            tenant_id=tenant_id,
            path=request.path,
            method=request.method,
        )

        # Store request ID in request object for response headers
        request.audit_request_id = request_id

        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Update context with user after authentication."""
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            set_audit_context(
                user_id=str(user.id),
                user_email=user.email,
                user_full_name=getattr(user, 'full_name', '')
            )
        return None

    def process_response(self, request, response):
        """Add request ID to response headers and clean up."""
        # Add request ID to response for client correlation
        request_id = getattr(request, 'audit_request_id', None)
        if request_id:
            response['X-Request-ID'] = request_id

        # Clear context at end of request
        clear_audit_context()

        return response

    def process_exception(self, request, exception):
        """Log exception in audit context."""
        set_audit_context(
            exception_type=type(exception).__name__,
            exception_message=str(exception)
        )
        return None

    def _get_client_ip(self, request):
        """Get the client IP address, handling proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the chain (original client)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AuditContextMixin:
    """
    Mixin for views to easily access audit context.

    Usage:
        class MyView(AuditContextMixin, APIView):
            def post(self, request):
                self.log_audit('create', record)
    """

    def get_audit_kwargs(self):
        """Get audit kwargs from current context."""
        context = get_audit_context()
        return {
            'ip_address': context.get('ip_address'),
            'user_agent': context.get('user_agent'),
            'request_id': context.get('request_id'),
            'tenant_id': context.get('tenant_id'),
        }

    def log_audit(
        self,
        action,
        record=None,
        old_values=None,
        new_values=None,
        changed_fields=None,
        description=''
    ):
        """
        Log an audit entry for the current request.

        Args:
            action: AuditLog.ActionType value
            record: The record being acted upon
            old_values: Previous field values (for updates)
            new_values: New field values (for updates)
            changed_fields: List of changed field names
            description: Human-readable description
        """
        from apps.audit.models import AuditLog
        from django.contrib.contenttypes.models import ContentType

        user = getattr(self.request, 'user', None)
        kwargs = self.get_audit_kwargs()

        content_type = None
        object_id = None
        record_type = ''
        record_identifier = ''

        if record:
            content_type = ContentType.objects.get_for_model(record)
            object_id = str(record.pk)
            record_type = content_type.model
            record_identifier = (
                getattr(record, 'batch_number', None) or
                getattr(record, 'identifier', None) or
                getattr(record, 'code', None) or
                str(record.pk)
            )

        return AuditLog.log_action(
            user=user if user and user.is_authenticated else None,
            action=action,
            record_type=record_type or 'system',
            object_id=object_id,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            description=description,
            content_type=content_type,
            record_identifier=record_identifier,
            **kwargs
        )
