"""
Workflow definition serializers.
"""
from rest_framework import serializers
from apps.workflow.models import (
    WorkflowDefinition,
    WorkflowState,
    WorkflowTransition,
    ApprovalRule,
)


class ApprovalRuleSerializer(serializers.ModelSerializer):
    """Serializer for approval rules."""

    class Meta:
        model = ApprovalRule
        fields = [
            'id',
            'name',
            'approval_type',
            'approver_roles',
            'min_approvals',
            'escalation_hours',
            'escalation_roles',
            'order',
        ]


class WorkflowTransitionSerializer(serializers.ModelSerializer):
    """Serializer for workflow transitions."""

    from_state_name = serializers.CharField(source='from_state.name', read_only=True)
    to_state_name = serializers.CharField(source='to_state.name', read_only=True)
    approval_rules = ApprovalRuleSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowTransition
        fields = [
            'id',
            'code',
            'name',
            'description',
            'from_state',
            'from_state_name',
            'to_state',
            'to_state_name',
            'transition_type',
            'required_permission',
            'required_roles',
            'conditions',
            'requires_approval',
            'approval_rules',
            'pre_actions',
            'post_actions',
            'order',
            'is_active',
            'button_label',
            'button_color',
        ]


class WorkflowStateSerializer(serializers.ModelSerializer):
    """Serializer for workflow states."""

    outgoing_transitions = WorkflowTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowState
        fields = [
            'id',
            'code',
            'name',
            'description',
            'state_type',
            'is_initial',
            'is_terminal',
            'color',
            'order',
            'required_actions',
            'required_signatures',
            'auto_transition_enabled',
            'timeout_hours',
            'timeout_action',
            'outgoing_transitions',
        ]


class WorkflowDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for workflow definitions."""

    states = WorkflowStateSerializer(many=True, read_only=True)
    transitions = WorkflowTransitionSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = WorkflowDefinition
        fields = [
            'id',
            'code',
            'name',
            'description',
            'version',
            'status',
            'applicable_record_types',
            'states',
            'transitions',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at', 'created_by']


class WorkflowDefinitionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for workflow definition lists."""

    state_count = serializers.SerializerMethodField()
    transition_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowDefinition
        fields = [
            'id',
            'code',
            'name',
            'version',
            'status',
            'applicable_record_types',
            'state_count',
            'transition_count',
            'created_at',
        ]

    def get_state_count(self, obj):
        return obj.states.count()

    def get_transition_count(self, obj):
        return obj.transitions.count()
