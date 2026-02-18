"""
Workflow Definition models.

Defines the structure and rules for workflows that can be
applied to batch records and other entities.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class WorkflowDefinition(TimeStampedModel):
    """
    A workflow definition that can be applied to records.

    Workflows consist of states and transitions, with approval
    requirements and conditional logic.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        DEPRECATED = 'deprecated', 'Deprecated'
        ARCHIVED = 'archived', 'Archived'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic info
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text='Unique code for this workflow'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Version control
    version = models.PositiveIntegerField(default=1)
    parent_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_versions',
        help_text='Previous version this was derived from'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # Record types this workflow applies to
    applicable_record_types = models.JSONField(
        default=list,
        help_text='List of record types this workflow can be applied to'
    )

    # Tenant scope (empty for global workflows)
    tenant_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Who created/modified
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_workflows'
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='modified_workflows',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'workflow_definitions'
        ordering = ['name', '-version']
        unique_together = ['code', 'version', 'tenant_id']

    def __str__(self):
        return f'{self.name} v{self.version}'

    def get_initial_state(self):
        """Get the initial state for this workflow."""
        return self.states.filter(is_initial=True).first()

    def get_terminal_states(self):
        """Get all terminal (final) states."""
        return self.states.filter(is_terminal=True)

    def create_new_version(self, user):
        """
        Create a new version of this workflow definition.

        Returns the new version instance (not saved).
        """
        new_def = WorkflowDefinition(
            code=self.code,
            name=self.name,
            description=self.description,
            version=self.version + 1,
            parent_version=self,
            applicable_record_types=self.applicable_record_types.copy(),
            tenant_id=self.tenant_id,
            created_by=user,
            status=self.Status.DRAFT
        )
        return new_def


class WorkflowState(TimeStampedModel):
    """
    A state within a workflow.

    States represent positions in the workflow where a record
    can exist. Records transition between states via transitions.
    """

    class StateType(models.TextChoices):
        INITIAL = 'initial', 'Initial'
        NORMAL = 'normal', 'Normal'
        APPROVAL = 'approval', 'Requires Approval'
        TERMINAL = 'terminal', 'Terminal'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Parent workflow
    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name='states'
    )

    # State info
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # State type
    state_type = models.CharField(
        max_length=20,
        choices=StateType.choices,
        default=StateType.NORMAL
    )
    is_initial = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)

    # Visual/UI properties
    color = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text='Hex color for UI display'
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text='Display order'
    )

    # Required actions in this state
    required_actions = models.JSONField(
        default=list,
        help_text='List of action codes that must be completed in this state'
    )

    # Signature requirements
    required_signatures = models.JSONField(
        default=list,
        help_text='List of signature meaning codes required to exit this state'
    )

    # Auto-transition settings
    auto_transition_enabled = models.BooleanField(
        default=False,
        help_text='Automatically transition when all requirements met'
    )
    auto_transition_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auto_sources',
        help_text='State to auto-transition to'
    )

    # Timeout settings
    timeout_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Hours before this state times out'
    )
    timeout_action = models.CharField(
        max_length=50,
        blank=True,
        help_text='Action to take on timeout (escalate, notify, transition)'
    )

    class Meta:
        db_table = 'workflow_states'
        ordering = ['workflow', 'order']
        unique_together = ['workflow', 'code']

    def __str__(self):
        return f'{self.workflow.name}: {self.name}'

    def get_outgoing_transitions(self):
        """Get all transitions that leave this state."""
        return self.outgoing_transitions.filter(is_active=True)


class WorkflowTransition(TimeStampedModel):
    """
    A transition between workflow states.

    Defines how a record can move from one state to another,
    including any conditions and approval requirements.
    """

    class TransitionType(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        AUTOMATIC = 'automatic', 'Automatic'
        APPROVAL = 'approval', 'Requires Approval'
        SCHEDULED = 'scheduled', 'Scheduled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Parent workflow
    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name='transitions'
    )

    # Transition info
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Source and target states
    from_state = models.ForeignKey(
        WorkflowState,
        on_delete=models.CASCADE,
        related_name='outgoing_transitions'
    )
    to_state = models.ForeignKey(
        WorkflowState,
        on_delete=models.CASCADE,
        related_name='incoming_transitions'
    )

    # Transition type
    transition_type = models.CharField(
        max_length=20,
        choices=TransitionType.choices,
        default=TransitionType.MANUAL
    )

    # Permissions required
    required_permission = models.CharField(
        max_length=100,
        blank=True,
        help_text='Permission code required to trigger this transition'
    )
    required_roles = models.JSONField(
        default=list,
        help_text='List of role codes that can trigger this transition'
    )

    # Conditions (JSON logic expression)
    conditions = models.JSONField(
        null=True,
        blank=True,
        help_text='JSON logic conditions that must be met'
    )

    # Approval requirements
    requires_approval = models.BooleanField(default=False)
    approval_config = models.JSONField(
        null=True,
        blank=True,
        help_text='Approval configuration (approvers, escalation, etc.)'
    )

    # Pre/post actions
    pre_actions = models.JSONField(
        default=list,
        help_text='Actions to execute before transition'
    )
    post_actions = models.JSONField(
        default=list,
        help_text='Actions to execute after transition'
    )

    # UI properties
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    button_label = models.CharField(
        max_length=100,
        blank=True,
        help_text='Label for the transition button in UI'
    )
    button_color = models.CharField(
        max_length=20,
        default='primary',
        help_text='Button color class (primary, success, warning, danger)'
    )

    class Meta:
        db_table = 'workflow_transitions'
        ordering = ['workflow', 'from_state', 'order']
        unique_together = ['workflow', 'code']

    def __str__(self):
        return f'{self.from_state.name} → {self.to_state.name}'

    def can_execute(self, user, record):
        """
        Check if the transition can be executed.

        Args:
            user: The user attempting the transition
            record: The record being transitioned

        Returns:
            Tuple of (can_execute, reason)
        """
        # Check permission
        if self.required_permission:
            user_permissions = user.get_all_permissions_set()
            if self.required_permission not in user_permissions:
                return False, 'Missing required permission'

        # Check roles
        if self.required_roles:
            user_roles = set(user.roles.values_list('code', flat=True))
            if not user_roles.intersection(set(self.required_roles)):
                return False, 'Missing required role'

        # Check conditions
        if self.conditions:
            from apps.workflow.engine.conditions import evaluate_conditions
            if not evaluate_conditions(self.conditions, record):
                return False, 'Conditions not met'

        return True, None


class ApprovalRule(TimeStampedModel):
    """
    Approval rule for a workflow transition.

    Defines who can approve and what's required for approval.
    """

    class ApprovalType(models.TextChoices):
        SINGLE = 'single', 'Single Approver'
        ALL = 'all', 'All Must Approve'
        ANY = 'any', 'Any One Approver'
        MAJORITY = 'majority', 'Majority Must Approve'
        SEQUENTIAL = 'sequential', 'Sequential Approval'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Parent transition
    transition = models.ForeignKey(
        WorkflowTransition,
        on_delete=models.CASCADE,
        related_name='approval_rules'
    )

    # Rule name
    name = models.CharField(max_length=255)

    # Approval type
    approval_type = models.CharField(
        max_length=20,
        choices=ApprovalType.choices,
        default=ApprovalType.SINGLE
    )

    # Who can approve
    approver_roles = models.JSONField(
        default=list,
        help_text='Role codes that can approve'
    )
    approver_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='approval_rules'
    )

    # Requirements
    min_approvals = models.PositiveIntegerField(
        default=1,
        help_text='Minimum approvals required'
    )

    # Escalation
    escalation_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Hours before escalation'
    )
    escalation_roles = models.JSONField(
        default=list,
        help_text='Roles to escalate to'
    )

    # Order for sequential approval
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'workflow_approval_rules'
        ordering = ['transition', 'order']

    def __str__(self):
        return f'{self.transition}: {self.name}'
