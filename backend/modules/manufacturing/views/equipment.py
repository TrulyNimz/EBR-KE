"""
Equipment and calibration views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from modules.manufacturing.models import (
    Equipment,
    CalibrationRecord,
    EquipmentUsage,
)
from modules.manufacturing.serializers import (
    EquipmentSerializer,
    EquipmentListSerializer,
    CalibrationRecordSerializer,
    CalibrationRecordCreateSerializer,
    EquipmentUsageSerializer,
    EquipmentUsageCreateSerializer,
)
from modules.manufacturing.serializers.equipment import EquipmentUsageCompleteSerializer
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class EquipmentViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Equipment."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.equipment.read'
    filterset_fields = ['equipment_type', 'status', 'location', 'requires_calibration']
    search_fields = ['equipment_id', 'name', 'serial_number', 'barcode']
    ordering = ['equipment_id']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return Equipment.objects.filter(tenant_id=tenant_id)

    def get_serializer_class(self):
        if self.action == 'list':
            return EquipmentListSerializer
        return EquipmentSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.equipment.create',
            'update': 'manufacturing.equipment.update',
            'partial_update': 'manufacturing.equipment.update',
            'destroy': 'manufacturing.equipment.delete',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.equipment.read')
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def calibration_due(self, request):
        """Get equipment with calibration due."""
        days_ahead = int(request.query_params.get('days', 30))
        cutoff = timezone.now().date() + timezone.timedelta(days=days_ahead)

        equipment = self.get_queryset().filter(
            requires_calibration=True,
            status=Equipment.Status.OPERATIONAL,
            next_calibration_date__lte=cutoff
        ).order_by('next_calibration_date')

        serializer = EquipmentListSerializer(equipment, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def maintenance_due(self, request):
        """Get equipment with maintenance due."""
        days_ahead = int(request.query_params.get('days', 30))
        cutoff = timezone.now().date() + timezone.timedelta(days=days_ahead)

        equipment = self.get_queryset().filter(
            requires_preventive_maintenance=True,
            status__in=[Equipment.Status.OPERATIONAL, Equipment.Status.CALIBRATION_DUE],
            next_maintenance_date__lte=cutoff
        ).order_by('next_maintenance_date')

        serializer = EquipmentListSerializer(equipment, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def scan(self, request):
        """Look up equipment by barcode scan."""
        barcode = request.query_params.get('barcode')
        if not barcode:
            return Response(
                {'error': 'Barcode parameter required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            equipment = self.get_queryset().get(
                Q(barcode=barcode) | Q(equipment_id=barcode)
            )
            return Response(EquipmentSerializer(equipment).data)
        except Equipment.DoesNotExist:
            return Response(
                {'error': 'Equipment not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def set_status(self, request, pk=None):
        """Update equipment status."""
        equipment = self.get_object()
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')

        if new_status not in dict(Equipment.Status.choices):
            return Response(
                {'error': 'Invalid status.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        equipment.status = new_status
        if reason:
            equipment.notes = f"Status changed to {new_status}: {reason}\n\n{equipment.notes}"
        equipment.modified_by = request.user
        equipment.save()

        return Response({
            'message': f'Equipment status updated to {new_status}.',
            'equipment': EquipmentSerializer(equipment).data
        })


class CalibrationRecordViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Calibration Records."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.calibration.read'
    filterset_fields = ['equipment', 'result', 'calibrated_by']
    ordering = ['-calibration_date']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return CalibrationRecord.objects.filter(
            equipment__tenant_id=tenant_id
        ).select_related('equipment', 'calibrated_by', 'reviewed_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return CalibrationRecordCreateSerializer
        return CalibrationRecordSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.calibration.create',
            'review': 'manufacturing.calibration.review',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.calibration.read')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Review and approve calibration record."""
        record = self.get_object()

        if record.reviewed_by:
            return Response(
                {'error': 'Record already reviewed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if record.calibrated_by == request.user:
            return Response(
                {'error': 'Cannot review your own calibration.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()

        return Response({
            'message': 'Calibration reviewed.',
            'record': CalibrationRecordSerializer(record).data
        })


class EquipmentUsageViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Equipment Usage records."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.equipment_usage.read'
    filterset_fields = ['equipment', 'batch', 'operated_by']
    ordering = ['-start_time']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return EquipmentUsage.objects.filter(
            equipment__tenant_id=tenant_id
        ).select_related('equipment', 'batch', 'operated_by', 'cleaning_completed_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return EquipmentUsageCreateSerializer
        return EquipmentUsageSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.equipment_usage.create',
            'complete': 'manufacturing.equipment_usage.complete',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.equipment_usage.read')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete equipment usage session."""
        usage = self.get_object()

        if usage.end_time:
            return Response(
                {'error': 'Usage already completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EquipmentUsageCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        usage.end_time = timezone.now()
        usage.parameters_recorded = data.get('parameters_recorded', usage.parameters_recorded)
        usage.issues_encountered = data.get('issues_encountered', False)
        usage.issue_details = data.get('issue_details', '')
        usage.notes = data.get('notes', usage.notes)

        if data.get('cleaning_completed'):
            usage.cleaning_completed = True
            usage.cleaning_completed_by = request.user
            usage.cleaning_completed_at = timezone.now()

        usage.modified_by = request.user
        usage.save()

        # If issues encountered, flag equipment
        if usage.issues_encountered:
            usage.equipment.status = Equipment.Status.UNDER_MAINTENANCE
            usage.equipment.notes = f"Issue reported: {usage.issue_details}\n\n{usage.equipment.notes}"
            usage.equipment.save()

        return Response({
            'message': 'Usage completed.',
            'usage': EquipmentUsageSerializer(usage).data
        })

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently active equipment usage sessions."""
        active_usages = self.get_queryset().filter(end_time__isnull=True)
        serializer = EquipmentUsageSerializer(active_usages, many=True)
        return Response(serializer.data)
