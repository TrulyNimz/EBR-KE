"""
Crop management views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum

from modules.agriculture.models import Crop, Field, CropBatch, FarmInput
from modules.agriculture.serializers import (
    CropSerializer,
    CropListSerializer,
    FieldSerializer,
    FieldListSerializer,
    CropBatchSerializer,
    CropBatchListSerializer,
    CropBatchCreateSerializer,
    FarmInputSerializer,
    FarmInputCreateSerializer,
)
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class CropViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Crops."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.crop.read'
    filterset_fields = ['crop_type', 'is_active', 'organic_certified']
    search_fields = ['code', 'name', 'variety', 'scientific_name']
    ordering = ['name']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return Crop.objects.filter(tenant_id=tenant_id)

    def get_serializer_class(self):
        if self.action == 'list':
            return CropListSerializer
        return CropSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'agriculture.crop.create',
            'update': 'agriculture.crop.update',
            'partial_update': 'agriculture.crop.update',
            'destroy': 'agriculture.crop.delete',
        }
        self.required_permission = permission_map.get(self.action, 'agriculture.crop.read')
        return super().get_permissions()


class FieldViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Fields."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.field.read'
    filterset_fields = ['soil_type', 'irrigation_type', 'is_active', 'organic_certified', 'current_status']
    search_fields = ['field_code', 'name', 'location_description']
    ordering = ['name']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return Field.objects.filter(tenant_id=tenant_id)

    def get_serializer_class(self):
        if self.action == 'list':
            return FieldListSerializer
        return FieldSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'agriculture.field.create',
            'update': 'agriculture.field.update',
            'partial_update': 'agriculture.field.update',
            'destroy': 'agriculture.field.delete',
        }
        self.required_permission = permission_map.get(self.action, 'agriculture.field.read')
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get field summary statistics."""
        queryset = self.get_queryset().filter(is_active=True)

        total_area = queryset.aggregate(total=Sum('area_hectares'))['total'] or 0
        planted = queryset.filter(current_status='planted').count()
        fallow = queryset.filter(current_status='fallow').count()
        organic = queryset.filter(organic_certified=True).count()

        return Response({
            'total_fields': queryset.count(),
            'total_area_hectares': float(total_area),
            'fields_planted': planted,
            'fields_fallow': fallow,
            'organic_certified': organic,
        })


class CropBatchViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Crop Batches."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.batch.read'
    filterset_fields = ['crop', 'field', 'status']
    search_fields = ['batch_number', 'seed_lot_number']
    ordering = ['-created_at']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return CropBatch.objects.filter(
            tenant_id=tenant_id
        ).select_related('crop', 'field')

    def get_serializer_class(self):
        if self.action == 'list':
            return CropBatchListSerializer
        if self.action == 'create':
            return CropBatchCreateSerializer
        return CropBatchSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'agriculture.batch.create',
            'update': 'agriculture.batch.update',
            'partial_update': 'agriculture.batch.update',
            'plant': 'agriculture.batch.plant',
            'harvest': 'agriculture.batch.harvest',
        }
        self.required_permission = permission_map.get(self.action, 'agriculture.batch.read')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def plant(self, request, pk=None):
        """Record planting of a crop batch."""
        batch = self.get_object()

        if batch.status != CropBatch.Status.PLANNED:
            return Response(
                {'error': f'Cannot plant batch with status: {batch.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        batch.status = CropBatch.Status.PLANTED
        batch.actual_planting_date = request.data.get('planting_date', timezone.now().date())
        batch.planting_method = request.data.get('planting_method', batch.planting_method)
        batch.modified_by = request.user
        batch.save()

        # Update field status
        batch.field.current_status = 'planted'
        batch.field.save()

        return Response({
            'message': 'Batch planted successfully.',
            'batch': CropBatchSerializer(batch).data
        })

    @action(detail=True, methods=['post'])
    def start_harvest(self, request, pk=None):
        """Start harvest of a crop batch."""
        batch = self.get_object()

        if batch.status not in [CropBatch.Status.GROWING, CropBatch.Status.READY_FOR_HARVEST]:
            return Response(
                {'error': f'Cannot harvest batch with status: {batch.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        batch.status = CropBatch.Status.HARVESTING
        batch.actual_harvest_start = timezone.now().date()
        batch.modified_by = request.user
        batch.save()

        return Response({
            'message': 'Harvest started.',
            'batch': CropBatchSerializer(batch).data
        })

    @action(detail=True, methods=['post'])
    def complete_harvest(self, request, pk=None):
        """Complete harvest of a crop batch."""
        batch = self.get_object()

        if batch.status != CropBatch.Status.HARVESTING:
            return Response(
                {'error': f'Cannot complete harvest for batch with status: {batch.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        harvest_quantity = request.data.get('harvest_quantity')
        if not harvest_quantity:
            return Response(
                {'error': 'Harvest quantity required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        batch.status = CropBatch.Status.HARVESTED
        batch.actual_harvest_end = timezone.now().date()
        batch.harvest_quantity = harvest_quantity
        batch.harvest_unit = request.data.get('harvest_unit', batch.harvest_unit)
        batch.quality_grade = request.data.get('quality_grade', '')
        batch.moisture_content = request.data.get('moisture_content')
        batch.storage_location = request.data.get('storage_location', '')

        # Calculate yield
        if batch.planted_area_hectares and float(batch.planted_area_hectares) > 0:
            batch.yield_per_hectare = float(harvest_quantity) / float(batch.planted_area_hectares)

        batch.modified_by = request.user
        batch.save()

        # Update field status
        batch.field.current_status = 'fallow'
        batch.field.save()

        return Response({
            'message': 'Harvest completed.',
            'batch': CropBatchSerializer(batch).data
        })

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active crop batches."""
        active_statuses = ['planted', 'growing', 'ready', 'harvesting']
        batches = self.get_queryset().filter(status__in=active_statuses)
        serializer = CropBatchListSerializer(batches, many=True)
        return Response(serializer.data)


class FarmInputViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Farm Inputs."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.input.read'
    http_method_names = ['get', 'post', 'head', 'options']
    filterset_fields = ['crop_batch', 'input_type', 'applied_by']
    search_fields = ['product_name', 'product_code']
    ordering = ['-application_date']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return FarmInput.objects.filter(
            crop_batch__tenant_id=tenant_id
        ).select_related('crop_batch', 'applied_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return FarmInputCreateSerializer
        return FarmInputSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'agriculture.input.create'
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def by_batch(self, request):
        """Get inputs for a specific batch."""
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response(
                {'error': 'batch_id parameter required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        inputs = self.get_queryset().filter(crop_batch_id=batch_id)
        serializer = FarmInputSerializer(inputs, many=True)
        return Response(serializer.data)
