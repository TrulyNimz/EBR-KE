"""
Livestock management views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Sum, Avg

from modules.agriculture.models import (
    AnimalSpecies,
    Animal,
    AnimalHealthRecord,
    AnimalProductionRecord,
)
from modules.agriculture.serializers import (
    AnimalSpeciesSerializer,
    AnimalSerializer,
    AnimalListSerializer,
    AnimalCreateSerializer,
    AnimalHealthRecordSerializer,
    AnimalHealthRecordCreateSerializer,
    AnimalProductionRecordSerializer,
    AnimalProductionRecordCreateSerializer,
)
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class AnimalSpeciesViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Animal Species."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.species.read'
    serializer_class = AnimalSpeciesSerializer
    filterset_fields = ['is_active']
    search_fields = ['code', 'name', 'scientific_name']
    ordering = ['name']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return AnimalSpecies.objects.filter(tenant_id=tenant_id)

    def get_permissions(self):
        permission_map = {
            'create': 'agriculture.species.create',
            'update': 'agriculture.species.update',
            'partial_update': 'agriculture.species.update',
        }
        self.required_permission = permission_map.get(self.action, 'agriculture.species.read')
        return super().get_permissions()


class AnimalViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Animals."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.animal.read'
    filterset_fields = ['species', 'sex', 'status', 'production_group', 'current_location']
    search_fields = ['tag_number', 'electronic_id', 'name']
    ordering = ['tag_number']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return Animal.objects.filter(
            tenant_id=tenant_id
        ).select_related('species', 'dam', 'sire')

    def get_serializer_class(self):
        if self.action == 'list':
            return AnimalListSerializer
        if self.action == 'create':
            return AnimalCreateSerializer
        return AnimalSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'agriculture.animal.create',
            'update': 'agriculture.animal.update',
            'partial_update': 'agriculture.animal.update',
            'destroy': 'agriculture.animal.delete',
        }
        self.required_permission = permission_map.get(self.action, 'agriculture.animal.read')
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def scan(self, request):
        """Look up animal by RFID/tag scan."""
        scan_value = request.query_params.get('id')
        if not scan_value:
            return Response(
                {'error': 'id parameter required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            animal = self.get_queryset().get(
                Q(tag_number=scan_value) | Q(electronic_id=scan_value)
            )
            return Response(AnimalSerializer(animal).data)
        except Animal.DoesNotExist:
            return Response(
                {'error': 'Animal not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def record_weight(self, request, pk=None):
        """Record animal weight."""
        animal = self.get_object()
        weight = request.data.get('weight')

        if not weight:
            return Response(
                {'error': 'Weight required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        animal.current_weight_kg = weight
        animal.last_weight_date = timezone.now().date()
        animal.modified_by = request.user
        animal.save()

        return Response({
            'message': 'Weight recorded.',
            'animal': AnimalSerializer(animal).data
        })

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update animal status."""
        animal = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        if new_status not in dict(Animal.Status.choices):
            return Response(
                {'error': 'Invalid status.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        animal.status = new_status
        animal.status_date = timezone.now().date()
        animal.status_notes = notes
        animal.modified_by = request.user
        animal.save()

        return Response({
            'message': f'Status updated to {new_status}.',
            'animal': AnimalSerializer(animal).data
        })

    @action(detail=False, methods=['get'])
    def herd_summary(self, request):
        """Get herd summary statistics."""
        queryset = self.get_queryset().filter(status='active')

        by_species = {}
        for species in AnimalSpecies.objects.filter(
            tenant_id=getattr(request, 'tenant_id', '')
        ):
            animals = queryset.filter(species=species)
            by_species[species.name] = {
                'total': animals.count(),
                'male': animals.filter(sex='male').count(),
                'female': animals.filter(sex='female').count(),
            }

        return Response({
            'total_active': queryset.count(),
            'by_species': by_species,
        })


class AnimalHealthRecordViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Animal Health Records."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.health.read'
    filterset_fields = ['animal', 'record_type', 'performed_by', 'follow_up_required']
    ordering = ['-record_date']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return AnimalHealthRecord.objects.filter(
            animal__tenant_id=tenant_id
        ).select_related('animal', 'performed_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return AnimalHealthRecordCreateSerializer
        return AnimalHealthRecordSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'agriculture.health.create',
        }
        self.required_permission = permission_map.get(self.action, 'agriculture.health.read')
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def follow_ups_due(self, request):
        """Get health records with follow-ups due."""
        today = timezone.now().date()
        days_ahead = int(request.query_params.get('days', 7))
        end_date = today + timezone.timedelta(days=days_ahead)

        records = self.get_queryset().filter(
            follow_up_required=True,
            follow_up_date__gte=today,
            follow_up_date__lte=end_date
        ).order_by('follow_up_date')

        serializer = AnimalHealthRecordSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def withdrawal_active(self, request):
        """Get animals currently under withdrawal period."""
        today = timezone.now().date()

        # Find recent treatments with withdrawal periods
        records = self.get_queryset().filter(
            withdrawal_period_days__isnull=False
        ).select_related('animal')

        active_withdrawals = []
        for record in records:
            withdrawal_end = record.record_date + timezone.timedelta(days=record.withdrawal_period_days)
            if withdrawal_end >= today:
                active_withdrawals.append({
                    'animal': AnimalListSerializer(record.animal).data,
                    'treatment_date': record.record_date,
                    'product': record.product_name,
                    'withdrawal_end': withdrawal_end,
                    'days_remaining': (withdrawal_end - today).days,
                })

        return Response(active_withdrawals)


class AnimalProductionRecordViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Animal Production Records."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'agriculture.production.read'
    http_method_names = ['get', 'post', 'head', 'options']
    filterset_fields = ['animal', 'production_type', 'recorded_by']
    ordering = ['-production_date']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return AnimalProductionRecord.objects.filter(
            animal__tenant_id=tenant_id
        ).select_related('animal', 'recorded_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return AnimalProductionRecordCreateSerializer
        return AnimalProductionRecordSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'agriculture.production.create'
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get production summary."""
        days = int(request.query_params.get('days', 30))
        production_type = request.query_params.get('type')
        cutoff = timezone.now().date() - timezone.timedelta(days=days)

        queryset = self.get_queryset().filter(production_date__gte=cutoff)
        if production_type:
            queryset = queryset.filter(production_type=production_type)

        summary = queryset.values('production_type', 'unit').annotate(
            total_quantity=Sum('quantity'),
            record_count=Sum(1),
            avg_quantity=Avg('quantity'),
        )

        return Response(list(summary))
