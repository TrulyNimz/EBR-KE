"""
Workflow instance views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.workflow.models import (
    WorkflowInstance,
    WorkflowTransition,
    ApprovalRequest,
)
from apps.workflow.serializers import (
    WorkflowInstanceSerializer,
    StateHistorySerializer,
    ApprovalRequestSerializer,
)
from apps.workflow.serializers.instances import (
    TransitionRequestSerializer,
    ApprovalDecisionRequestSerializer,
)
from apps.workflow.engine import WorkflowEngine
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class WorkflowInstanceViewSet(AuditContextMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Workflow Instances.

    GET  /api/v1/workflow-instances/           - List instances
    GET  /api/v1/workflow-instances/{id}/      - Get instance details
    POST /api/v1/workflow-instances/{id}/transition/ - Execute transition
    GET  /api/v1/workflow-instances/{id}/history/    - Get state history
    """
    serializer_class = WorkflowInstanceSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'workflow.instance.read'
    filterset_fields = ['workflow', 'status', 'current_state']
    ordering = ['-started_at']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return WorkflowInstance.objects.filter(
            tenant_id=tenant_id
        ).select_related('workflow', 'current_state', 'started_by')

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        """Execute a workflow transition."""
        instance = self.get_object()
        serializer = TransitionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transition_id = serializer.validated_data['transition_id']
        notes = serializer.validated_data.get('notes', '')

        try:
            transition = WorkflowTransition.objects.get(id=transition_id)
        except WorkflowTransition.DoesNotExist:
            return Response(
                {'error': 'Transition not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        engine = WorkflowEngine(instance)
        success, message, approval_request = engine.execute_transition(
            transition,
            request.user,
            notes=notes
        )

        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

        response_data = {
            'message': message,
            'instance': WorkflowInstanceSerializer(
                instance,
                context={'request': request}
            ).data
        }

        if approval_request:
            response_data['approval_request'] = ApprovalRequestSerializer(
                approval_request
            ).data

        return Response(response_data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get state history for an instance."""
        instance = self.get_object()
        history = instance.state_history.all().order_by('transitioned_at')
        serializer = StateHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def available_transitions(self, request, pk=None):
        """Get available transitions for current user."""
        instance = self.get_object()
        engine = WorkflowEngine(instance)
        transitions = engine.get_available_transitions(request.user)

        from apps.workflow.serializers.definitions import WorkflowTransitionSerializer

        result = []
        for transition, can_execute, reason in transitions:
            data = WorkflowTransitionSerializer(transition).data
            data['can_execute'] = can_execute
            data['reason'] = reason
            result.append(data)

        return Response(result)


class ApprovalRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Approval Requests.

    GET  /api/v1/approval-requests/           - List pending approvals
    GET  /api/v1/approval-requests/{id}/      - Get approval details
    POST /api/v1/approval-requests/{id}/decide/ - Make approval decision
    """
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'workflow.approval.read'
    filterset_fields = ['status', 'instance__workflow']
    ordering = ['-requested_at']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        queryset = ApprovalRequest.objects.filter(
            instance__tenant_id=tenant_id
        ).select_related('instance', 'transition', 'approval_rule', 'requested_by')

        # Filter to show only requests the user can approve
        if not self.request.user.is_staff:
            user_roles = list(self.request.user.roles.values_list('code', flat=True))
            queryset = queryset.filter(
                approval_rule__approver_roles__overlap=user_roles
            ) | queryset.filter(
                approval_rule__approver_users=self.request.user
            )

        return queryset.distinct()

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending approval requests for current user."""
        queryset = self.get_queryset().filter(status=ApprovalRequest.Status.PENDING)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        """Make an approval decision."""
        approval_request = self.get_object()
        serializer = ApprovalDecisionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data['decision']
        comments = serializer.validated_data.get('comments', '')

        # Check if user can approve
        user_roles = set(request.user.roles.values_list('code', flat=True))
        allowed_roles = set(approval_request.approval_rule.approver_roles or [])
        is_explicit_approver = approval_request.approval_rule.approver_users.filter(
            id=request.user.id
        ).exists()

        if not user_roles.intersection(allowed_roles) and not is_explicit_approver:
            return Response(
                {'error': 'You are not authorized to approve this request.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Process the approval
        engine = WorkflowEngine(approval_request.instance)
        success, message = engine.process_approval(
            approval_request,
            request.user,
            decision,
            comments
        )

        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': message,
            'approval_request': ApprovalRequestSerializer(approval_request).data
        })
