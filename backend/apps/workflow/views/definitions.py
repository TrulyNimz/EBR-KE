"""
Workflow definition views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.workflow.models import WorkflowDefinition, WorkflowState, WorkflowTransition
from apps.workflow.serializers import (
    WorkflowDefinitionSerializer,
    WorkflowStateSerializer,
    WorkflowTransitionSerializer,
)
from apps.workflow.serializers.definitions import WorkflowDefinitionListSerializer
from apps.iam.permissions import RBACPermission


class WorkflowDefinitionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Workflow Definitions.

    GET    /api/v1/workflows/           - List workflows
    POST   /api/v1/workflows/           - Create workflow
    GET    /api/v1/workflows/{id}/      - Get workflow details
    PATCH  /api/v1/workflows/{id}/      - Update workflow
    DELETE /api/v1/workflows/{id}/      - Delete workflow
    POST   /api/v1/workflows/{id}/activate/   - Activate workflow
    POST   /api/v1/workflows/{id}/deprecate/  - Deprecate workflow
    POST   /api/v1/workflows/{id}/new-version/ - Create new version
    """
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'workflow.definition.read'
    filterset_fields = ['status', 'applicable_record_types']
    search_fields = ['code', 'name', 'description']
    ordering = ['name', '-version']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return WorkflowDefinition.objects.filter(
            tenant_id__in=[tenant_id, '']  # Include global workflows
        ).prefetch_related('states', 'transitions')

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowDefinitionListSerializer
        return WorkflowDefinitionSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'workflow.definition.create'
        elif self.action in ['update', 'partial_update', 'activate', 'deprecate']:
            self.required_permission = 'workflow.definition.update'
        elif self.action == 'destroy':
            self.required_permission = 'workflow.definition.delete'
        return super().get_permissions()

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', '')
        serializer.save(created_by=self.request.user, tenant_id=tenant_id)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a workflow definition."""
        workflow = self.get_object()
        if workflow.status != WorkflowDefinition.Status.DRAFT:
            return Response(
                {'error': 'Only draft workflows can be activated.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate workflow has required components
        if not workflow.states.filter(is_initial=True).exists():
            return Response(
                {'error': 'Workflow must have an initial state.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not workflow.states.filter(is_terminal=True).exists():
            return Response(
                {'error': 'Workflow must have at least one terminal state.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        workflow.status = WorkflowDefinition.Status.ACTIVE
        workflow.modified_by = request.user
        workflow.save(update_fields=['status', 'modified_by', 'updated_at'])

        return Response({'message': f'Workflow {workflow.name} activated.'})

    @action(detail=True, methods=['post'])
    def deprecate(self, request, pk=None):
        """Deprecate a workflow definition."""
        workflow = self.get_object()
        if workflow.status != WorkflowDefinition.Status.ACTIVE:
            return Response(
                {'error': 'Only active workflows can be deprecated.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        workflow.status = WorkflowDefinition.Status.DEPRECATED
        workflow.modified_by = request.user
        workflow.save(update_fields=['status', 'modified_by', 'updated_at'])

        return Response({'message': f'Workflow {workflow.name} deprecated.'})

    @action(detail=True, methods=['post'])
    def new_version(self, request, pk=None):
        """Create a new version of a workflow."""
        workflow = self.get_object()
        new_workflow = workflow.create_new_version(request.user)
        new_workflow.save()

        # Copy states and transitions
        state_mapping = {}
        for state in workflow.states.all():
            new_state = WorkflowState.objects.create(
                workflow=new_workflow,
                code=state.code,
                name=state.name,
                description=state.description,
                state_type=state.state_type,
                is_initial=state.is_initial,
                is_terminal=state.is_terminal,
                color=state.color,
                order=state.order,
                required_actions=state.required_actions,
                required_signatures=state.required_signatures,
                auto_transition_enabled=state.auto_transition_enabled,
                timeout_hours=state.timeout_hours,
                timeout_action=state.timeout_action,
            )
            state_mapping[state.id] = new_state

        # Copy transitions
        for transition in workflow.transitions.all():
            WorkflowTransition.objects.create(
                workflow=new_workflow,
                code=transition.code,
                name=transition.name,
                description=transition.description,
                from_state=state_mapping[transition.from_state_id],
                to_state=state_mapping[transition.to_state_id],
                transition_type=transition.transition_type,
                required_permission=transition.required_permission,
                required_roles=transition.required_roles,
                conditions=transition.conditions,
                requires_approval=transition.requires_approval,
                approval_config=transition.approval_config,
                pre_actions=transition.pre_actions,
                post_actions=transition.post_actions,
                order=transition.order,
                is_active=transition.is_active,
                button_label=transition.button_label,
                button_color=transition.button_color,
            )

        return Response(
            WorkflowDefinitionSerializer(new_workflow).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def states(self, request, pk=None):
        """Get all states for a workflow."""
        workflow = self.get_object()
        states = workflow.states.all().order_by('order')
        serializer = WorkflowStateSerializer(states, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def transitions(self, request, pk=None):
        """Get all transitions for a workflow."""
        workflow = self.get_object()
        transitions = workflow.transitions.all().order_by('from_state', 'order')
        serializer = WorkflowTransitionSerializer(transitions, many=True)
        return Response(serializer.data)
