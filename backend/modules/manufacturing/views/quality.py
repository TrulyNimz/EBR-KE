"""
Quality control views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from modules.manufacturing.models import (
    QCTest,
    QCTestRequest,
    QCResult,
    BatchRelease,
)
from modules.manufacturing.serializers import (
    QCTestSerializer,
    QCTestRequestSerializer,
    QCTestRequestCreateSerializer,
    QCResultSerializer,
    QCResultCreateSerializer,
    BatchReleaseSerializer,
    BatchReleaseCreateSerializer,
)
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class QCTestViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for QC Test definitions."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.qctest.read'
    filterset_fields = ['test_type', 'is_active']
    search_fields = ['code', 'name', 'method_reference']
    ordering = ['name']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return QCTest.objects.filter(tenant_id=tenant_id)

    def get_serializer_class(self):
        return QCTestSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.qctest.create',
            'update': 'manufacturing.qctest.update',
            'partial_update': 'manufacturing.qctest.update',
            'destroy': 'manufacturing.qctest.delete',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.qctest.read')
        return super().get_permissions()


class QCTestRequestViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for QC Test Requests."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.qcrequest.read'
    filterset_fields = ['sample_type', 'status', 'priority', 'requested_by']
    search_fields = ['request_number', 'sample_description']
    ordering = ['-requested_at']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return QCTestRequest.objects.filter(
            tenant_id=tenant_id
        ).select_related('batch', 'material_lot', 'requested_by').prefetch_related('tests', 'results')

    def get_serializer_class(self):
        if self.action == 'create':
            return QCTestRequestCreateSerializer
        return QCTestRequestSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.qcrequest.create',
            'start': 'manufacturing.qcrequest.start',
            'complete': 'manufacturing.qcrequest.complete',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.qcrequest.read')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start testing on a QC request."""
        qc_request = self.get_object()

        if qc_request.status != QCTestRequest.Status.PENDING:
            return Response(
                {'error': f'Cannot start. Current status: {qc_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qc_request.status = QCTestRequest.Status.IN_PROGRESS
        qc_request.modified_by = request.user
        qc_request.save()

        return Response({
            'message': 'Testing started.',
            'request': QCTestRequestSerializer(qc_request).data
        })

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a QC request."""
        qc_request = self.get_object()

        if qc_request.status != QCTestRequest.Status.IN_PROGRESS:
            return Response(
                {'error': f'Cannot complete. Current status: {qc_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check all tests have results
        tests_count = qc_request.tests.count()
        results_count = qc_request.results.exclude(outcome=QCResult.Outcome.PENDING).count()

        if results_count < tests_count:
            return Response(
                {'error': f'Not all tests completed. {results_count}/{tests_count} done.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qc_request.status = QCTestRequest.Status.COMPLETED
        qc_request.completed_at = timezone.now()
        qc_request.modified_by = request.user
        qc_request.save()

        # Update material lot status if applicable
        if qc_request.material_lot:
            all_passed = not qc_request.results.filter(outcome=QCResult.Outcome.FAIL).exists()
            qc_request.material_lot.status = 'pending_qc'  # Ready for approval
            qc_request.material_lot.qc_sample_taken = True
            qc_request.material_lot.save()

        return Response({
            'message': 'QC request completed.',
            'request': QCTestRequestSerializer(qc_request).data
        })

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending QC requests."""
        pending = self.get_queryset().filter(status=QCTestRequest.Status.PENDING)
        serializer = QCTestRequestSerializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue QC requests."""
        overdue = self.get_queryset().filter(
            due_date__lt=timezone.now(),
            status__in=[QCTestRequest.Status.PENDING, QCTestRequest.Status.IN_PROGRESS]
        )
        serializer = QCTestRequestSerializer(overdue, many=True)
        return Response(serializer.data)


class QCResultViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for QC Results."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.qcresult.read'
    http_method_names = ['get', 'post', 'head', 'options']
    filterset_fields = ['request', 'test', 'outcome', 'tested_by']
    ordering = ['-tested_at']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return QCResult.objects.filter(
            request__tenant_id=tenant_id
        ).select_related('request', 'test', 'tested_by', 'reviewed_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return QCResultCreateSerializer
        return QCResultSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.qcresult.create',
            'review': 'manufacturing.qcresult.review',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.qcresult.read')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Review a QC result."""
        result = self.get_object()

        if result.reviewed_by:
            return Response(
                {'error': 'Result already reviewed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if result.tested_by == request.user:
            return Response(
                {'error': 'Cannot review your own result.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result.reviewed_by = request.user
        result.reviewed_at = timezone.now()
        result.save()

        return Response({
            'message': 'Result reviewed.',
            'result': QCResultSerializer(result).data
        })


class BatchReleaseViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Batch Release decisions."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.release.read'
    filterset_fields = ['decision', 'decision_by']
    search_fields = ['batch__batch_number']
    ordering = ['-decision_date']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return BatchRelease.objects.filter(
            tenant_id=tenant_id
        ).select_related('batch', 'decision_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return BatchReleaseCreateSerializer
        return BatchReleaseSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.release.create',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.release.read')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def generate_coa(self, request, pk=None):
        """Generate Certificate of Analysis for released batch."""
        release = self.get_object()

        if release.decision != BatchRelease.Decision.RELEASED:
            return Response(
                {'error': 'COA can only be generated for released batches.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # TODO: Implement COA generation logic
        release.coa_generated = True
        release.save()

        return Response({
            'message': 'COA generation initiated.',
            'release': BatchReleaseSerializer(release).data
        })
