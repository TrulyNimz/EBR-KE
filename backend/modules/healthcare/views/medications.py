"""
Medication management views with 5 Rights verification.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from modules.healthcare.models import MedicationOrder, MedicationAdministration
from modules.healthcare.serializers import (
    MedicationOrderSerializer,
    MedicationOrderCreateSerializer,
    MedicationAdministrationSerializer,
    MedicationAdministrationCreateSerializer,
    FiveRightsVerificationSerializer,
)
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class MedicationOrderViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """
    ViewSet for Medication Orders.

    Endpoints:
        GET    /api/v1/healthcare/medication-orders/           - List orders
        POST   /api/v1/healthcare/medication-orders/           - Create order
        GET    /api/v1/healthcare/medication-orders/{id}/      - Get order
        PATCH  /api/v1/healthcare/medication-orders/{id}/      - Update order
        POST   /api/v1/healthcare/medication-orders/{id}/verify/     - Verify order
        POST   /api/v1/healthcare/medication-orders/{id}/discontinue/ - Discontinue
        POST   /api/v1/healthcare/medication-orders/{id}/verify-5rights/ - 5 Rights check
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'healthcare.medication.read'
    filterset_fields = ['patient', 'status', 'prescriber']
    search_fields = ['order_number', 'medication_name', 'medication_code']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter by tenant with related data."""
        tenant_id = getattr(self.request, 'tenant_id', '')
        return MedicationOrder.objects.filter(
            tenant_id=tenant_id
        ).select_related(
            'patient',
            'prescriber',
            'verified_by',
        )

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MedicationOrderCreateSerializer
        return MedicationOrderSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'healthcare.medication.prescribe',
            'update': 'healthcare.medication.update',
            'partial_update': 'healthcare.medication.update',
            'verify': 'healthcare.medication.verify',
            'discontinue': 'healthcare.medication.discontinue',
        }
        self.required_permission = permission_map.get(
            self.action, 'healthcare.medication.read'
        )
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Pharmacist verification of medication order."""
        order = self.get_object()

        if order.verified_by:
            return Response(
                {'error': 'Order already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.prescriber == request.user:
            return Response(
                {'error': 'Prescriber cannot verify their own order.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.verified_by = request.user
        order.verified_at = timezone.now()
        order.save(update_fields=['verified_by', 'verified_at', 'updated_at'])

        return Response({
            'message': 'Medication order verified',
            'order': MedicationOrderSerializer(order).data
        })

    @action(detail=True, methods=['post'])
    def discontinue(self, request, pk=None):
        """Discontinue a medication order."""
        order = self.get_object()

        if order.status == MedicationOrder.Status.DISCONTINUED:
            return Response(
                {'error': 'Order already discontinued.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = MedicationOrder.Status.DISCONTINUED
        order.end_date = timezone.now()
        order.modified_by = request.user
        order.save(update_fields=['status', 'end_date', 'modified_by', 'updated_at'])

        return Response({
            'message': 'Medication order discontinued',
            'order': MedicationOrderSerializer(order).data
        })

    @action(detail=True, methods=['post'], url_path='verify-5rights')
    def verify_five_rights(self, request, pk=None):
        """
        Perform 5 Rights verification for medication administration.

        This is a pre-check before actual administration to verify:
        1. Right Patient (wristband scan)
        2. Right Medication (barcode scan)
        3. Right Dose
        4. Right Route
        5. Right Time
        """
        order = self.get_object()

        serializer = FiveRightsVerificationSerializer(
            data=request.data,
            context={'order': order, 'request': request}
        )
        serializer.is_valid(raise_exception=True)

        return Response({
            'verification': serializer.validated_data,
            'can_administer': serializer.validated_data['all_verified'],
        })

    @action(detail=True, methods=['get'])
    def administrations(self, request, pk=None):
        """Get administration history for an order."""
        order = self.get_object()
        administrations = order.administrations.all().order_by('-administered_at')
        serializer = MedicationAdministrationSerializer(administrations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active medication orders for a patient."""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id query parameter required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        orders = self.get_queryset().filter(
            patient_id=patient_id,
            status=MedicationOrder.Status.ACTIVE
        )
        serializer = MedicationOrderSerializer(orders, many=True)
        return Response(serializer.data)


class MedicationAdministrationViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """
    ViewSet for Medication Administration records.

    Endpoints:
        GET  /api/v1/healthcare/medication-administrations/      - List administrations
        POST /api/v1/healthcare/medication-administrations/      - Record administration
        GET  /api/v1/healthcare/medication-administrations/{id}/ - Get record
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'healthcare.medication.administer'
    http_method_names = ['get', 'post', 'head', 'options']  # No updates/deletes
    filterset_fields = ['order', 'order__patient', 'status', 'administered_by']
    ordering = ['-administered_at']

    def get_queryset(self):
        """Filter by tenant."""
        tenant_id = getattr(self.request, 'tenant_id', '')
        return MedicationAdministration.objects.filter(
            order__tenant_id=tenant_id
        ).select_related(
            'order',
            'order__patient',
            'administered_by',
            'witnessed_by',
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return MedicationAdministrationCreateSerializer
        return MedicationAdministrationSerializer

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            self.required_permission = 'healthcare.medication.read'
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def due(self, request):
        """
        Get medications due for administration.

        Query params:
            patient_id: Filter by patient (optional)
            ward: Filter by ward (optional)
        """
        patient_id = request.query_params.get('patient_id')
        ward = request.query_params.get('ward')

        from modules.healthcare.models import Patient

        tenant_id = getattr(request, 'tenant_id', '')
        now = timezone.now()

        # Get active orders that are due
        orders = MedicationOrder.objects.filter(
            tenant_id=tenant_id,
            status=MedicationOrder.Status.ACTIVE,
            start_date__lte=now,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        ).select_related('patient')

        if patient_id:
            orders = orders.filter(patient_id=patient_id)

        if ward:
            orders = orders.filter(patient__ward=ward)

        serializer = MedicationOrderSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent administrations for audit/review."""
        hours = int(request.query_params.get('hours', 24))
        cutoff = timezone.now() - timezone.timedelta(hours=hours)

        queryset = self.get_queryset().filter(
            administered_at__gte=cutoff
        )[:100]

        serializer = MedicationAdministrationSerializer(queryset, many=True)
        return Response(serializer.data)
