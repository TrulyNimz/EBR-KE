"""
Traceability views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from modules.agriculture.models import TraceabilityRecord, CertificationRecord
from modules.agriculture.serializers import (
    TraceabilityRecordSerializer,
    TraceabilityRecordCreateSerializer,
    CertificationRecordSerializer,
    CertificationRecordCreateSerializer,
)
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class TraceabilityRecordViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Traceability Records."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.traceability.read'
    filterset_fields = ['event_type', 'verified', 'handled_by']
    search_fields = ['trace_code', 'product_description', 'event_location']
    ordering = ['-event_date']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return TraceabilityRecord.objects.filter(
            tenant_id=tenant_id
        ).select_related('handled_by', 'verified_by', 'previous_record')

    def get_serializer_class(self):
        if self.action == 'create':
            return TraceabilityRecordCreateSerializer
        return TraceabilityRecordSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'agriculture.traceability.create',
            'verify': 'agriculture.traceability.verify',
        }
        self.required_permission = permission_map.get(self.action, 'agriculture.traceability.read')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a traceability record."""
        record = self.get_object()

        if record.verified:
            return Response(
                {'error': 'Record already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if record.handled_by == request.user:
            return Response(
                {'error': 'Cannot verify your own record.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        record.verified = True
        record.verified_by = request.user
        record.verified_at = timezone.now()
        record.save()

        return Response({
            'message': 'Record verified.',
            'record': TraceabilityRecordSerializer(record).data
        })

    @action(detail=False, methods=['get'])
    def trace(self, request):
        """
        Get full traceability chain for a trace code.

        Query params:
            trace_code: The trace code to look up
        """
        trace_code = request.query_params.get('trace_code')
        if not trace_code:
            return Response(
                {'error': 'trace_code parameter required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        chain = TraceabilityRecord.get_chain_for_product(trace_code)
        if not chain:
            return Response(
                {'error': 'Trace code not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'trace_code': trace_code,
            'chain': [
                {
                    'trace_code': r.trace_code,
                    'event_type': r.event_type,
                    'event_date': r.event_date,
                    'event_location': r.event_location,
                    'product_description': r.product_description,
                    'quantity': r.quantity,
                    'unit': r.unit,
                    'from_party': r.from_party,
                    'to_party': r.to_party,
                    'certifications': r.certifications,
                    'verified': r.verified,
                }
                for r in chain
            ]
        })

    @action(detail=False, methods=['get'])
    def qr_code(self, request):
        """
        Generate QR code data for a trace code.

        This returns the data to be encoded; actual QR generation is client-side.
        """
        trace_code = request.query_params.get('trace_code')
        if not trace_code:
            return Response(
                {'error': 'trace_code parameter required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            record = self.get_queryset().get(trace_code=trace_code)
        except TraceabilityRecord.DoesNotExist:
            return Response(
                {'error': 'Trace code not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Build consumer-facing trace URL
        base_url = request.build_absolute_uri('/').rstrip('/')
        trace_url = f"{base_url}/trace/{trace_code}"

        return Response({
            'trace_code': trace_code,
            'trace_url': trace_url,
            'product': record.product_description,
            'origin': record.event_location,
            'certifications': record.certifications,
        })


class CertificationRecordViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Certification Records."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.certification.read'
    filterset_fields = ['certification_type', 'is_valid']
    search_fields = ['certification_name', 'certificate_number', 'certifying_body']
    ordering = ['-issued_date']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return CertificationRecord.objects.filter(tenant_id=tenant_id)

    def get_serializer_class(self):
        if self.action == 'create':
            return CertificationRecordCreateSerializer
        return CertificationRecordSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'agriculture.certification.create',
            'update': 'agriculture.certification.update',
            'partial_update': 'agriculture.certification.update',
        }
        self.required_permission = permission_map.get(self.action, 'agriculture.certification.read')
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get certifications expiring within specified days."""
        days = int(request.query_params.get('days', 90))
        today = timezone.now().date()
        cutoff = today + timezone.timedelta(days=days)

        expiring = self.get_queryset().filter(
            is_valid=True,
            expiry_date__gte=today,
            expiry_date__lte=cutoff
        ).order_by('expiry_date')

        serializer = CertificationRecordSerializer(expiring, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def audits_due(self, request):
        """Get certifications with audits due."""
        days = int(request.query_params.get('days', 30))
        today = timezone.now().date()
        cutoff = today + timezone.timedelta(days=days)

        audits_due = self.get_queryset().filter(
            is_valid=True,
            next_audit_date__gte=today,
            next_audit_date__lte=cutoff
        ).order_by('next_audit_date')

        serializer = CertificationRecordSerializer(audits_due, many=True)
        return Response(serializer.data)
