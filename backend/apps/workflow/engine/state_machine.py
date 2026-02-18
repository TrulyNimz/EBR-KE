"""
State Machine Engine.

Core engine for executing workflow transitions and managing
workflow state.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional, Dict, Any

from django.db import transaction
from django.utils import timezone as django_timezone

from apps.workflow.models import (
    WorkflowDefinition,
    WorkflowState,
    WorkflowTransition,
    WorkflowInstance,
    StateHistory,
    ApprovalRequest,
    ApprovalDecision,
)
from apps.audit.models import AuditLog


class WorkflowEngine:
    """
    Engine for executing workflow operations.

    Provides methods for:
    - Starting workflows
    - Executing transitions
    - Managing approvals
    - Checking state timeouts
    """

    def __init__(self, instance: WorkflowInstance):
        """
        Initialize the engine for a workflow instance.

        Args:
            instance: The WorkflowInstance to operate on.
        """
        self.instance = instance
        self.workflow = instance.workflow
        self.current_state = instance.current_state

    @classmethod
    def start_workflow(
        cls,
        workflow: WorkflowDefinition,
        record,
        user,
        context_data: Optional[Dict] = None,
        tenant_id: str = ''
    ) -> 'WorkflowEngine':
        """
        Start a new workflow for a record.

        Args:
            workflow: The workflow definition to use.
            record: The Django model instance.
            user: The user starting the workflow.
            context_data: Optional context data.
            tenant_id: Optional tenant ID.

        Returns:
            WorkflowEngine instance for the new workflow.
        """
        instance = WorkflowInstance.start_workflow(
            workflow=workflow,
            record=record,
            user=user,
            context_data=context_data,
            tenant_id=tenant_id
        )

        # Log to audit trail
        AuditLog.log_action(
            user=user,
            action=AuditLog.ActionType.WORKFLOW_TRANSITION,
            record_type=instance.content_type.model,
            object_id=str(record.pk),
            description=f'Started workflow: {workflow.name}',
            new_values={'state': instance.current_state.code},
            tenant_id=tenant_id
        )

        return cls(instance)

    def get_available_transitions(self, user) -> List[Tuple[WorkflowTransition, bool, str]]:
        """
        Get all transitions available from the current state.

        Args:
            user: The user requesting transitions.

        Returns:
            List of tuples: (transition, can_execute, reason)
        """
        transitions = self.current_state.get_outgoing_transitions()
        results = []

        for transition in transitions:
            record = self.instance.content_object
            can_execute, reason = transition.can_execute(user, record)
            results.append((transition, can_execute, reason or ''))

        return results

    def can_execute_transition(self, transition: WorkflowTransition, user) -> Tuple[bool, str]:
        """
        Check if a specific transition can be executed.

        Args:
            transition: The transition to check.
            user: The user attempting the transition.

        Returns:
            Tuple of (can_execute, reason)
        """
        # Verify transition is from current state
        if transition.from_state_id != self.current_state.id:
            return False, 'Transition not available from current state'

        # Verify transition belongs to this workflow
        if transition.workflow_id != self.workflow.id:
            return False, 'Transition not part of this workflow'

        # Check transition's own conditions
        record = self.instance.content_object
        return transition.can_execute(user, record)

    @transaction.atomic
    def execute_transition(
        self,
        transition: WorkflowTransition,
        user,
        notes: str = '',
        skip_approval: bool = False
    ) -> Tuple[bool, str, Optional[ApprovalRequest]]:
        """
        Execute a workflow transition.

        Args:
            transition: The transition to execute.
            user: The user triggering the transition.
            notes: Optional notes for the transition.
            skip_approval: Skip approval (for auto-transitions).

        Returns:
            Tuple of (success, message, approval_request if created)
        """
        # Check if transition can be executed
        can_execute, reason = self.can_execute_transition(transition, user)
        if not can_execute:
            return False, reason, None

        record = self.instance.content_object

        # Check if approval is required
        if transition.requires_approval and not skip_approval:
            approval_request = self._create_approval_request(transition, user, notes)
            return True, 'Approval request created', approval_request

        # Calculate time in previous state
        time_in_state = django_timezone.now() - self.instance.state_entered_at

        # Execute pre-actions
        self._execute_actions(transition.pre_actions, record, user)

        # Record the transition
        previous_state = self.current_state
        new_state = transition.to_state

        # Create state history entry
        StateHistory.objects.create(
            instance=self.instance,
            from_state=previous_state,
            to_state=new_state,
            transition=transition,
            triggered_by=user,
            action=transition.code,
            notes=notes,
            time_in_state=time_in_state
        )

        # Update instance
        self.instance.current_state = new_state
        self.instance.state_entered_at = django_timezone.now()

        # Set deadline if state has timeout
        if new_state.timeout_hours:
            self.instance.state_deadline = django_timezone.now() + timedelta(
                hours=new_state.timeout_hours
            )
        else:
            self.instance.state_deadline = None

        # Check if workflow is complete
        if new_state.is_terminal:
            self.instance.status = WorkflowInstance.Status.COMPLETED
            self.instance.completed_at = django_timezone.now()
            self.instance.completed_by = user

        self.instance.save()
        self.current_state = new_state

        # Execute post-actions
        self._execute_actions(transition.post_actions, record, user)

        # Log to audit trail
        AuditLog.log_action(
            user=user,
            action=AuditLog.ActionType.WORKFLOW_TRANSITION,
            record_type=self.instance.content_type.model,
            object_id=str(record.pk),
            description=f'Transitioned: {previous_state.name} → {new_state.name}',
            old_values={'state': previous_state.code},
            new_values={'state': new_state.code},
            tenant_id=self.instance.tenant_id
        )

        # Check for auto-transition
        if new_state.auto_transition_enabled and new_state.auto_transition_to:
            self._check_auto_transition(user)

        return True, f'Transitioned to {new_state.name}', None

    def _create_approval_request(
        self,
        transition: WorkflowTransition,
        user,
        notes: str
    ) -> ApprovalRequest:
        """Create an approval request for a transition."""
        # Get the first approval rule
        approval_rule = transition.approval_rules.first()
        if not approval_rule:
            raise ValueError('Transition requires approval but has no approval rules')

        # Calculate deadline
        deadline = None
        if approval_rule.escalation_hours:
            deadline = django_timezone.now() + timedelta(
                hours=approval_rule.escalation_hours
            )

        # Create snapshot of record
        record = self.instance.content_object
        record_snapshot = {}
        if hasattr(record, 'to_dict'):
            record_snapshot = record.to_dict()
        elif hasattr(record, '__dict__'):
            record_snapshot = {
                k: str(v) for k, v in record.__dict__.items()
                if not k.startswith('_')
            }

        return ApprovalRequest.objects.create(
            instance=self.instance,
            transition=transition,
            approval_rule=approval_rule,
            requested_by=user,
            request_notes=notes,
            deadline=deadline,
            record_snapshot=record_snapshot
        )

    @transaction.atomic
    def process_approval(
        self,
        request: ApprovalRequest,
        user,
        decision: str,
        comments: str = '',
        signature=None
    ) -> Tuple[bool, str]:
        """
        Process an approval decision.

        Args:
            request: The approval request.
            user: The user making the decision.
            decision: 'approved' or 'rejected'.
            comments: Optional comments.
            signature: Optional digital signature.

        Returns:
            Tuple of (success, message)
        """
        if request.status != ApprovalRequest.Status.PENDING:
            return False, 'Approval request is not pending'

        # Create decision record
        ApprovalDecision.objects.create(
            request=request,
            decision=decision,
            decided_by=user,
            comments=comments,
            signature=signature
        )

        # Check if approval requirements are met
        rule = request.approval_rule
        decisions = request.decisions.all()
        approved_count = decisions.filter(
            decision=ApprovalDecision.Decision.APPROVED
        ).count()
        rejected_count = decisions.filter(
            decision=ApprovalDecision.Decision.REJECTED
        ).count()

        if rejected_count > 0:
            # Any rejection means the request is rejected
            request.status = ApprovalRequest.Status.REJECTED
            request.save()
            return True, 'Approval request rejected'

        if rule.approval_type == rule.ApprovalType.SINGLE:
            if approved_count >= 1:
                request.status = ApprovalRequest.Status.APPROVED
                request.save()
                # Execute the transition
                return self.execute_transition(
                    request.transition,
                    request.requested_by,
                    notes=f'Approved by {user.email}',
                    skip_approval=True
                )[:2]

        elif rule.approval_type == rule.ApprovalType.ALL:
            # Need to check if all required approvers have approved
            # For now, use min_approvals
            if approved_count >= rule.min_approvals:
                request.status = ApprovalRequest.Status.APPROVED
                request.save()
                return self.execute_transition(
                    request.transition,
                    request.requested_by,
                    notes=f'Approved by multiple approvers',
                    skip_approval=True
                )[:2]

        elif rule.approval_type == rule.ApprovalType.ANY:
            if approved_count >= 1:
                request.status = ApprovalRequest.Status.APPROVED
                request.save()
                return self.execute_transition(
                    request.transition,
                    request.requested_by,
                    notes=f'Approved by {user.email}',
                    skip_approval=True
                )[:2]

        return True, 'Decision recorded, waiting for more approvals'

    def _check_auto_transition(self, user):
        """Check and execute auto-transition if conditions are met."""
        state = self.current_state
        if not state.auto_transition_enabled or not state.auto_transition_to:
            return

        # Find the transition to the auto-transition target
        transition = WorkflowTransition.objects.filter(
            workflow=self.workflow,
            from_state=state,
            to_state=state.auto_transition_to,
            is_active=True
        ).first()

        if transition:
            can_execute, reason = self.can_execute_transition(transition, user)
            if can_execute:
                self.execute_transition(
                    transition,
                    user,
                    notes='Auto-transition',
                    skip_approval=True
                )

    def _execute_actions(self, actions: List[Dict], record, user):
        """Execute pre or post actions."""
        for action in actions:
            action_type = action.get('type')
            if action_type == 'notification':
                self._send_notification(action, record, user)
            elif action_type == 'update_field':
                self._update_field(action, record)
            elif action_type == 'webhook':
                self._call_webhook(action, record)
            # Add more action types as needed

    def _send_notification(self, action: Dict, record, user):
        """Send a notification (placeholder)."""
        # TODO: Implement notification sending
        pass

    def _update_field(self, action: Dict, record):
        """Update a field on the record."""
        field_name = action.get('field')
        value = action.get('value')
        if field_name and hasattr(record, field_name):
            setattr(record, field_name, value)
            record.save(update_fields=[field_name])

    def _call_webhook(self, action: Dict, record):
        """Call a webhook (placeholder)."""
        # TODO: Implement webhook calling
        pass

    @classmethod
    def check_timed_out_states(cls) -> List[WorkflowInstance]:
        """
        Find and handle instances with timed-out states.

        Returns:
            List of instances that were processed.
        """
        now = django_timezone.now()
        timed_out = WorkflowInstance.objects.filter(
            status=WorkflowInstance.Status.ACTIVE,
            state_deadline__lt=now
        ).select_related('current_state')

        processed = []
        for instance in timed_out:
            engine = cls(instance)
            engine._handle_timeout()
            processed.append(instance)

        return processed

    def _handle_timeout(self):
        """Handle state timeout."""
        state = self.current_state
        timeout_action = state.timeout_action

        if timeout_action == 'escalate':
            # Escalate any pending approval requests
            pending_requests = self.instance.approval_requests.filter(
                status=ApprovalRequest.Status.PENDING
            )
            for request in pending_requests:
                request.status = ApprovalRequest.Status.ESCALATED
                request.save()

        elif timeout_action == 'notify':
            # Send notification (placeholder)
            pass

        elif timeout_action == 'transition':
            # Find timeout transition
            timeout_transition = WorkflowTransition.objects.filter(
                workflow=self.workflow,
                from_state=state,
                code__contains='timeout',
                is_active=True
            ).first()

            if timeout_transition:
                # Use system user for timeout transitions
                from apps.iam.models import User
                system_user = User.objects.filter(email='system@ebr.local').first()
                if system_user:
                    self.execute_transition(
                        timeout_transition,
                        system_user,
                        notes='Auto-transition due to timeout',
                        skip_approval=True
                    )
