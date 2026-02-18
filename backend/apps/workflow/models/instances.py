"""
Workflow Instance models.

Tracks the execution of workflows on records.
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.core.models import TimeStampedModel


class WorkflowInstance(TimeStampedModel):
    """
    An instance of a workflow attached to a record.

    Tracks the current state and history of a record's
    progression through a workflow.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        SUSPENDED = 'suspended', 'Suspended'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The workflow definition
    workflow = models.ForeignKey(
        'workflow.WorkflowDefinition',
        on_delete=models.PROTECT,
        related_name='instances'
    )

    # Current state
    current_state = models.ForeignKey(
        'workflow.WorkflowState',
        on_delete=models.PROTECT,
        related_name='current_instances'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # The record this workflow is attached to
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    state_entered_at = models.DateTimeField(auto_now_add=True)
    state_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Deadline for current state based on timeout settings'
    )

    # Who started/completed
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='started_workflows'
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='completed_workflows'
    )

    # Context data for the workflow
    context_data = models.JSONField(
        default=dict,
        help_text='Additional context data for workflow execution'
    )

    # Tenant
    tenant_id = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        db_table = 'workflow_instances'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status', 'state_deadline']),
        ]

    def __str__(self):
        return f'{self.workflow.name} - {self.current_state.name}'

    @classmethod
    def start_workflow(cls, workflow, record, user, context_data=None, tenant_id=''):
        """
        Start a new workflow for a record.

        Args:
            workflow: WorkflowDefinition to start
            record: The Django model instance
            user: User starting the workflow
            context_data: Optional context data
            tenant_id: Optional tenant ID

        Returns:
            The created WorkflowInstance
        """
        initial_state = workflow.get_initial_state()
        if not initial_state:
            raise ValueError(f'Workflow {workflow.name} has no initial state')

        content_type = ContentType.objects.get_for_model(record)

        instance = cls.objects.create(
            workflow=workflow,
            current_state=initial_state,
            content_type=content_type,
            object_id=str(record.pk),
            started_by=user,
            context_data=context_data or {},
            tenant_id=tenant_id
        )

        # Create initial state history entry
        StateHistory.objects.create(
            instance=instance,
            from_state=None,
            to_state=initial_state,
            triggered_by=user,
            action='workflow_started',
            notes='Workflow started'
        )

        return instance


class StateHistory(models.Model):
    """
    Immutable history of state transitions.

    FDA 21 CFR Part 11 requires complete audit trail of all
    state changes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Parent instance
    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name='state_history'
    )

    # State change
    from_state = models.ForeignKey(
        'workflow.WorkflowState',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+'
    )
    to_state = models.ForeignKey(
        'workflow.WorkflowState',
        on_delete=models.PROTECT,
        related_name='+'
    )

    # Transition used (if any)
    transition = models.ForeignKey(
        'workflow.WorkflowTransition',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='executions'
    )

    # Timing
    transitioned_at = models.DateTimeField(auto_now_add=True)
    time_in_state = models.DurationField(
        null=True,
        blank=True,
        help_text='Duration spent in the from_state'
    )

    # Who triggered
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='state_transitions'
    )

    # Action and notes
    action = models.CharField(max_length=100)
    notes = models.TextField(blank=True)

    # Conditions evaluation result
    conditions_evaluated = models.JSONField(
        null=True,
        blank=True,
        help_text='Result of condition evaluation at transition time'
    )

    # Integrity
    checksum = models.CharField(
        max_length=64,
        editable=False,
        help_text='SHA-256 checksum for integrity'
    )

    class Meta:
        db_table = 'workflow_state_history'
        ordering = ['instance', 'transitioned_at']
        # Prevent updates and deletes at DB level if possible

    def __str__(self):
        from_name = self.from_state.name if self.from_state else 'Start'
        return f'{from_name} → {self.to_state.name}'

    def save(self, *args, **kwargs):
        import hashlib
        import json

        if self.pk and StateHistory.objects.filter(pk=self.pk).exists():
            raise PermissionError('State history cannot be modified.')

        # Calculate checksum
        hash_data = {
            'instance_id': str(self.instance_id),
            'from_state': str(self.from_state_id) if self.from_state_id else None,
            'to_state': str(self.to_state_id),
            'triggered_by': str(self.triggered_by_id),
            'action': self.action,
            'notes': self.notes,
        }
        hash_str = json.dumps(hash_data, sort_keys=True)
        self.checksum = hashlib.sha256(hash_str.encode()).hexdigest()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('State history cannot be deleted.')


class ApprovalRequest(TimeStampedModel):
    """
    A pending approval request.

    Created when a transition requires approval.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        ESCALATED = 'escalated', 'Escalated'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Workflow context
    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name='approval_requests'
    )
    transition = models.ForeignKey(
        'workflow.WorkflowTransition',
        on_delete=models.PROTECT,
        related_name='approval_requests'
    )
    approval_rule = models.ForeignKey(
        'workflow.ApprovalRule',
        on_delete=models.PROTECT,
        related_name='requests'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Who requested and who approved/rejected
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requested_approvals'
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    # Deadline
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Deadline for this approval'
    )

    # Notes
    request_notes = models.TextField(
        blank=True,
        help_text='Notes from the requester'
    )

    # Record snapshot at request time
    record_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text='Snapshot of record data at request time'
    )

    class Meta:
        db_table = 'workflow_approval_requests'
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.transition.name} - {self.status}'


class ApprovalDecision(models.Model):
    """
    An approval/rejection decision.

    Immutable record of an approver's decision.
    """

    class Decision(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Parent request
    request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name='decisions'
    )

    # Decision
    decision = models.CharField(
        max_length=20,
        choices=Decision.choices
    )
    decided_at = models.DateTimeField(auto_now_add=True)

    # Decider
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='approval_decisions'
    )

    # Comments
    comments = models.TextField(blank=True)

    # Digital signature (if required)
    signature = models.ForeignKey(
        'audit.DigitalSignature',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approval_decisions'
    )

    class Meta:
        db_table = 'workflow_approval_decisions'
        ordering = ['request', '-decided_at']

    def __str__(self):
        return f'{self.decided_by}: {self.decision}'

    def save(self, *args, **kwargs):
        if self.pk and ApprovalDecision.objects.filter(pk=self.pk).exists():
            raise PermissionError('Approval decisions cannot be modified.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('Approval decisions cannot be deleted.')
