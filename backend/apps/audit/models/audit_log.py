"""
Immutable Audit Log model for FDA 21 CFR Part 11 compliance.

Audit logs cannot be modified or deleted once created.
Each entry includes a hash chain link to the previous entry.
"""
import hashlib
import json
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class ImmutableManager(models.Manager):
    """
    Custom manager that prevents updates and deletes.

    FDA 21 CFR Part 11 requires audit trails to be immutable.
    """

    def update(self, **kwargs):
        raise PermissionError('Audit logs cannot be updated.')

    def delete(self, *args, **kwargs):
        raise PermissionError('Audit logs cannot be deleted.')


class AuditLogQuerySet(models.QuerySet):
    """QuerySet that prevents updates and deletes."""

    def update(self, **kwargs):
        raise PermissionError('Audit logs cannot be updated.')

    def delete(self, *args, **kwargs):
        raise PermissionError('Audit logs cannot be deleted.')


class AuditLog(models.Model):
    """
    Immutable audit log entry.

    Captures all changes to records with complete change tracking
    and hash chain integrity for tamper detection.
    """

    class ActionType(models.TextChoices):
        CREATE = 'create', 'Created'
        UPDATE = 'update', 'Updated'
        DELETE = 'delete', 'Deleted'
        VIEW = 'view', 'Viewed'
        EXPORT = 'export', 'Exported'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        LOGIN_FAILED = 'login_failed', 'Login Failed'
        PASSWORD_CHANGE = 'password_change', 'Password Changed'
        PERMISSION_CHANGE = 'permission_change', 'Permission Changed'
        APPROVAL = 'approval', 'Approved'
        REJECTION = 'rejection', 'Rejected'
        SIGNATURE = 'signature', 'Signed'
        WORKFLOW_TRANSITION = 'workflow_transition', 'Workflow Transition'

    # Primary key - UUID for uniqueness
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Timestamp - when the action occurred
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # User who performed the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    user_email = models.EmailField(
        help_text='Stored separately in case user is deleted'
    )
    user_full_name = models.CharField(max_length=255, blank=True)

    # Action details
    action = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        db_index=True
    )
    action_description = models.TextField(blank=True)

    # Target record (generic foreign key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    object_id = models.CharField(max_length=255, null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Additional record identifiers for compliance reporting
    record_type = models.CharField(max_length=100, db_index=True)
    record_identifier = models.CharField(
        max_length=255,
        blank=True,
        help_text='Human-readable identifier (e.g., batch number)'
    )

    # Change details (JSON)
    old_values = models.JSONField(
        null=True,
        blank=True,
        help_text='Previous state of changed fields'
    )
    new_values = models.JSONField(
        null=True,
        blank=True,
        help_text='New state of changed fields'
    )
    changed_fields = models.JSONField(
        default=list,
        help_text='List of field names that changed'
    )

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(
        max_length=64,
        blank=True,
        help_text='Correlation ID for request tracing'
    )

    # Tenant context (multi-tenancy)
    tenant_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Integrity chain
    previous_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text='Hash of the previous audit entry'
    )
    entry_hash = models.CharField(
        max_length=64,
        editable=False,
        help_text='Hash of this entry for integrity verification'
    )
    sequence_number = models.BigIntegerField(
        default=0,
        help_text='Sequential number for ordering and gap detection'
    )

    # Use immutable manager
    objects = ImmutableManager.from_queryset(AuditLogQuerySet)()

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp', '-sequence_number']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['record_type', 'object_id']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['tenant_id', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.timestamp} - {self.user_email} - {self.action} - {self.record_type}'

    def save(self, *args, **kwargs):
        """Save with integrity hash calculation."""
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError('Audit logs cannot be modified after creation.')

        # Get the previous entry hash
        last_entry = AuditLog.objects.order_by('-sequence_number').first()
        if last_entry:
            self.previous_hash = last_entry.entry_hash
            self.sequence_number = last_entry.sequence_number + 1
        else:
            self.previous_hash = '0' * 64  # Genesis entry
            self.sequence_number = 1

        # Calculate entry hash
        self.entry_hash = self._calculate_hash()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion."""
        raise PermissionError('Audit logs cannot be deleted.')

    def _calculate_hash(self):
        """
        Calculate SHA-256 hash of the entry.

        Includes all meaningful fields to detect any tampering.
        """
        hash_data = {
            'timestamp': str(self.timestamp) if self.timestamp else '',
            'user_email': self.user_email,
            'action': self.action,
            'record_type': self.record_type,
            'object_id': str(self.object_id) if self.object_id else '',
            'old_values': json.dumps(self.old_values, sort_keys=True, default=str),
            'new_values': json.dumps(self.new_values, sort_keys=True, default=str),
            'changed_fields': json.dumps(self.changed_fields, sort_keys=True),
            'previous_hash': self.previous_hash,
            'sequence_number': str(self.sequence_number),
        }
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def verify_integrity(self):
        """Verify this entry has not been tampered with."""
        expected_hash = self._calculate_hash()
        return self.entry_hash == expected_hash

    @classmethod
    def verify_chain_integrity(cls, start_sequence=None, end_sequence=None):
        """
        Verify the integrity of the audit chain.

        Returns list of entries with integrity issues.
        """
        queryset = cls.objects.all().order_by('sequence_number')

        if start_sequence:
            queryset = queryset.filter(sequence_number__gte=start_sequence)
        if end_sequence:
            queryset = queryset.filter(sequence_number__lte=end_sequence)

        issues = []
        previous_hash = None
        previous_sequence = None

        for entry in queryset.iterator():
            # Check for sequence gaps
            if previous_sequence is not None:
                if entry.sequence_number != previous_sequence + 1:
                    issues.append({
                        'entry_id': str(entry.id),
                        'issue': 'sequence_gap',
                        'expected_sequence': previous_sequence + 1,
                        'actual_sequence': entry.sequence_number
                    })

            # Check entry hash
            if not entry.verify_integrity():
                issues.append({
                    'entry_id': str(entry.id),
                    'issue': 'hash_mismatch',
                    'stored_hash': entry.entry_hash
                })

            # Check chain link
            if previous_hash is not None and entry.previous_hash != previous_hash:
                issues.append({
                    'entry_id': str(entry.id),
                    'issue': 'chain_broken',
                    'expected_previous': previous_hash,
                    'actual_previous': entry.previous_hash
                })

            previous_hash = entry.entry_hash
            previous_sequence = entry.sequence_number

        return issues

    @classmethod
    def log_action(
        cls,
        user,
        action,
        record_type,
        object_id=None,
        old_values=None,
        new_values=None,
        changed_fields=None,
        description='',
        ip_address=None,
        user_agent='',
        request_id='',
        tenant_id='',
        content_type=None,
        record_identifier=''
    ):
        """
        Create an audit log entry.

        This is the primary method for logging audit events.
        """
        entry = cls(
            user=user,
            user_email=user.email if user else 'system@ebr.local',
            user_full_name=user.full_name if user else 'System',
            action=action,
            action_description=description,
            record_type=record_type,
            object_id=str(object_id) if object_id else None,
            content_type=content_type,
            record_identifier=record_identifier,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields or [],
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            tenant_id=tenant_id
        )
        entry.save()
        return entry
