"""
Batch Records views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters import rest_framework as filters

from apps.batch_records.models import (
    Batch,
    BatchTemplate,
    BatchStep,
    BatchAttachment,
)
from apps.batch_records.serializers import (
    BatchSerializer,
    BatchListSerializer,
    BatchCreateSerializer,
    BatchTemplateSerializer,
    BatchStepSerializer,
    BatchStepExecuteSerializer,
    BatchAttachmentSerializer,
)
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin
from apps.audit.models import AuditLog


class BatchFilter(filters.FilterSet):
    """Filter for batches."""

    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    batch_number = filters.CharFilter(lookup_expr='icontains')
    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Batch
        fields = [
            'status',
            'priority',
            'module_type',
            'product_code',
            'batch_number',
            'name',
            'created_after',
            'created_before',
        ]


class BatchViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """
    ViewSet for Batch management.

    GET    /api/v1/batches/           - List batches
    POST   /api/v1/batches/           - Create batch
    GET    /api/v1/batches/{id}/      - Get batch details
    PATCH  /api/v1/batches/{id}/      - Update batch
    DELETE /api/v1/batches/{id}/      - Delete batch
    POST   /api/v1/batches/{id}/start/    - Start batch
    POST   /api/v1/batches/{id}/complete/ - Complete batch
    """
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'batch_records.batch.read'
    filterset_class = BatchFilter
    search_fields = ['batch_number', 'name', 'product_name']
    ordering_fields = ['created_at', 'batch_number', 'status', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return Batch.objects.filter(
            tenant_id=tenant_id,
            is_deleted=False
        ).select_related('template', 'created_by', 'modified_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return BatchListSerializer
        elif self.action == 'create':
            return BatchCreateSerializer
        return BatchSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'batch_records.batch.create'
        elif self.action in ['update', 'partial_update']:
            self.required_permission = 'batch_records.batch.update'
        elif self.action == 'destroy':
            self.required_permission = 'batch_records.batch.delete'
        elif self.action in ['start', 'complete']:
            self.required_permission = 'batch_records.batch.execute'
        return super().get_permissions()

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete."""
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start batch execution. Returns the updated Batch object."""
        batch = self.get_object()
        prev_status = batch.status
        try:
            batch.start(request.user)
            self.log_audit(
                AuditLog.ActionType.UPDATE,
                batch,
                old_values={'status': prev_status},
                new_values={'status': Batch.Status.IN_PROGRESS},
                changed_fields=['status', 'actual_start'],
                description='Batch started'
            )
            return Response(BatchSerializer(batch, context={'request': request}).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete batch execution. Returns the updated Batch object."""
        batch = self.get_object()
        prev_status = batch.status
        try:
            batch.complete(request.user)
            self.log_audit(
                AuditLog.ActionType.UPDATE,
                batch,
                old_values={'status': prev_status},
                new_values={'status': Batch.Status.COMPLETED},
                changed_fields=['status', 'actual_end'],
                description='Batch completed'
            )
            return Response(BatchSerializer(batch, context={'request': request}).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def audit_trail(self, request, pk=None):
        """Get audit trail for this batch."""
        batch = self.get_object()
        from apps.audit.serializers import AuditLogSerializer
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(batch)
        logs = AuditLog.objects.filter(
            content_type=content_type,
            object_id=str(batch.pk)
        ).order_by('-timestamp')

        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def signatures(self, request, pk=None):
        """Get digital signatures for this batch."""
        batch = self.get_object()
        from apps.audit.serializers import DigitalSignatureSerializer

        signatures = batch.signatures.all().select_related('meaning', 'signer')
        serializer = DigitalSignatureSerializer(signatures, many=True)
        return Response(serializer.data)


class BatchStepViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """
    ViewSet for Batch Step management.

    Nested under batches: /api/v1/batches/{batch_id}/steps/
    """
    serializer_class = BatchStepSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'batch_records.step.read'

    def get_queryset(self):
        batch_id = self.kwargs.get('batch_pk')
        return BatchStep.objects.filter(
            batch_id=batch_id
        ).select_related('executed_by', 'verified_by', 'template')

    def get_permissions(self):
        if self.action in ['execute', 'complete']:
            self.required_permission = 'batch_records.step.execute'
        elif self.action == 'verify':
            self.required_permission = 'batch_records.step.verify'
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def start(self, request, batch_pk=None, pk=None):
        """Start executing a step. Returns the updated BatchStep object."""
        step = self.get_object()
        try:
            step.start(request.user)
            return Response(BatchStepSerializer(step).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, batch_pk=None, pk=None):
        """Complete a step with data."""
        step = self.get_object()
        serializer = BatchStepExecuteSerializer(
            data=request.data,
            context={'step': step}
        )
        serializer.is_valid(raise_exception=True)

        try:
            step.data = serializer.validated_data.get('data', {})
            step.has_deviation = serializer.validated_data.get('has_deviation', False)
            step.deviation_notes = serializer.validated_data.get('deviation_notes', '')
            step.complete(request.user, step.data)

            self.log_audit(
                AuditLog.ActionType.UPDATE,
                step,
                new_values={'status': 'completed', 'data': step.data},
                changed_fields=['status', 'data', 'completed_at'],
                description=f'Step completed: {step.name}'
            )

            return Response(BatchStepSerializer(step).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def verify(self, request, batch_pk=None, pk=None):
        """Verify a completed step."""
        from django.utils import timezone

        step = self.get_object()
        if step.status != BatchStep.Status.COMPLETED:
            return Response(
                {'error': 'Step must be completed before verification.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        step.verified_by = request.user
        step.verified_at = timezone.now()
        step.save(update_fields=['verified_by', 'verified_at'])

        self.log_audit(
            AuditLog.ActionType.VERIFICATION,
            step,
            description=f'Step verified: {step.name}'
        )

        return Response({'message': f'Step {step.name} verified.'})


class BatchTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Batch Template management.

    GET    /api/v1/batch-templates/
    POST   /api/v1/batch-templates/
    GET    /api/v1/batch-templates/{id}/
    PATCH  /api/v1/batch-templates/{id}/
    DELETE /api/v1/batch-templates/{id}/
    """
    serializer_class = BatchTemplateSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'batch_records.template.read'
    filterset_fields = ['status', 'module_type', 'product_code']
    search_fields = ['code', 'name', 'product_name']
    ordering = ['name', '-version']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return BatchTemplate.objects.filter(
            tenant_id=tenant_id,
            is_deleted=False
        ).prefetch_related('step_templates')

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'batch_records.template.create'
        elif self.action in ['update', 'partial_update']:
            self.required_permission = 'batch_records.template.update'
        elif self.action == 'destroy':
            self.required_permission = 'batch_records.template.delete'
        return super().get_permissions()

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', '')
        serializer.save(created_by=self.request.user, tenant_id=tenant_id)

    @action(detail=True, methods=['post'])
    def create_batch(self, request, pk=None):
        """Create a new batch from this template."""
        template = self.get_object()
        batch_number = request.data.get('batch_number')

        if not batch_number:
            return Response(
                {'error': 'batch_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            batch = template.create_batch(
                request.user,
                batch_number,
                **{k: v for k, v in request.data.items() if k != 'batch_number'}
            )
            return Response(
                BatchSerializer(batch).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BatchAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Batch Attachments.

    Supports file upload with multipart form data.
    """
    serializer_class = BatchAttachmentSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'batch_records.attachment.read'
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        batch_id = self.kwargs.get('batch_pk')
        return BatchAttachment.objects.filter(
            batch_id=batch_id,
            is_deleted=False
        )

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'batch_records.attachment.create'
        elif self.action == 'destroy':
            self.required_permission = 'batch_records.attachment.delete'
        return super().get_permissions()

    def perform_create(self, serializer):
        batch_id = self.kwargs.get('batch_pk')
        uploaded_file = self.request.FILES.get('file')

        serializer.save(
            batch_id=batch_id,
            created_by=self.request.user,
            filename=uploaded_file.name if uploaded_file else '',
            file_size=uploaded_file.size if uploaded_file else 0,
            content_type=uploaded_file.content_type if uploaded_file else ''
        )
