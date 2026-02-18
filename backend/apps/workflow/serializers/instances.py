"""
Workflow instance serializers.
"""
from rest_framework import serializers
from apps.workflow.models import (
    WorkflowInstance,
    StateHistory,
    ApprovalRequest,
    ApprovalDecision,
)


class StateHistorySerializer(serializers.ModelSerializer):
    """Serializer for state history entries."""

    from_state_name = serializers.CharField(
        source='from_state.name',
        read_only=True,
        allow_null=True
    )
    to_state_name = serializers.CharField(source='to_state.name', read_only=True)
    triggered_by_name = serializers.CharField(
        source='triggered_by.full_name',
        read_only=True
    )

    class Meta:
        model = StateHistory
        fields = [
            'id',
            'from_state',
            'from_state_name',
            'to_state',
            'to_state_name',
            'transition',
            'transitioned_at',
            'time_in_state',
            'triggered_by',
            'triggered_by_name',
            'action',
            'notes',
        ]


class ApprovalDecisionSerializer(serializers.ModelSerializer):
    """Serializer for approval decisions."""

    decided_by_name = serializers.CharField(source='decided_by.full_name', read_only=True)

    class Meta:
        model = ApprovalDecision
        fields = [
            'id',
            'decision',
            'decided_at',
            'decided_by',
            'decided_by_name',
            'comments',
            'signature',
        ]


class ApprovalRequestSerializer(serializers.ModelSerializer):
    """Serializer for approval requests."""

    decisions = ApprovalDecisionSerializer(many=True, read_only=True)
    requested_by_name = serializers.CharField(
        source='requested_by.full_name',
        read_only=True
    )
    transition_name = serializers.CharField(source='transition.name', read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            'id',
            'instance',
            'transition',
            'transition_name',
            'approval_rule',
            'status',
            'requested_by',
            'requested_by_name',
            'requested_at',
            'deadline',
            'request_notes',
            'decisions',
        ]


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    """Serializer for workflow instances."""

    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    current_state_name = serializers.CharField(
        source='current_state.name',
        read_only=True
    )
    current_state_color = serializers.CharField(
        source='current_state.color',
        read_only=True
    )
    state_history = StateHistorySerializer(many=True, read_only=True)
    pending_approvals = serializers.SerializerMethodField()
    available_transitions = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = [
            'id',
            'workflow',
            'workflow_name',
            'current_state',
            'current_state_name',
            'current_state_color',
            'status',
            'content_type',
            'object_id',
            'started_at',
            'completed_at',
            'state_entered_at',
            'state_deadline',
            'started_by',
            'completed_by',
            'context_data',
            'state_history',
            'pending_approvals',
            'available_transitions',
        ]

    def get_pending_approvals(self, obj):
        requests = obj.approval_requests.filter(status='pending')
        return ApprovalRequestSerializer(requests, many=True).data

    def get_available_transitions(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user:
            return []

        from apps.workflow.engine import WorkflowEngine
        from apps.workflow.serializers.definitions import WorkflowTransitionSerializer

        engine = WorkflowEngine(obj)
        transitions = engine.get_available_transitions(user)

        result = []
        for transition, can_execute, reason in transitions:
            data = WorkflowTransitionSerializer(transition).data
            data['can_execute'] = can_execute
            data['reason'] = reason
            result.append(data)

        return result


class TransitionRequestSerializer(serializers.Serializer):
    """Serializer for requesting a workflow transition."""

    transition_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_transition_id(self, value):
        from apps.workflow.models import WorkflowTransition
        try:
            WorkflowTransition.objects.get(id=value)
        except WorkflowTransition.DoesNotExist:
            raise serializers.ValidationError('Transition not found.')
        return value


class ApprovalDecisionRequestSerializer(serializers.Serializer):
    """Serializer for making an approval decision."""

    decision = serializers.ChoiceField(choices=['approved', 'rejected'])
    comments = serializers.CharField(required=False, allow_blank=True, default='')
    password = serializers.CharField(
        write_only=True,
        required=False,
        help_text='Required for digital signature'
    )
