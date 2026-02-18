"""
Patient views with PHI access controls.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from modules.healthcare.models import Patient, PatientAllergy
from modules.healthcare.serializers import (
    PatientSerializer,
    PatientListSerializer,
    PatientCreateSerializer,
    PatientAllergySerializer,
)
from modules.healthcare.serializers.patients import (
    PatientAdmissionSerializer,
    PatientDischargeSerializer,
)
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class PatientViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """
    ViewSet for Patient management.

    Includes PHI access auditing and encryption handling.

    Endpoints:
        GET    /api/v1/healthcare/patients/           - List patients
        POST   /api/v1/healthcare/patients/           - Create patient
        GET    /api/v1/healthcare/patients/{id}/      - Get patient details
        PATCH  /api/v1/healthcare/patients/{id}/      - Update patient
        DELETE /api/v1/healthcare/patients/{id}/      - Delete patient (soft)
        POST   /api/v1/healthcare/patients/{id}/admit/     - Admit patient
        POST   /api/v1/healthcare/patients/{id}/discharge/ - Discharge patient
        GET    /api/v1/healthcare/patients/search/    - Search patients
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'healthcare.patient.read'
    filterset_fields = ['status', 'gender', 'ward', 'attending_physician']
    search_fields = ['patient_number', 'first_name', 'last_name', 'medical_record_number']
    ordering_fields = ['created_at', 'last_name', 'patient_number', 'admission_date']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter by tenant and apply optimizations."""
        tenant_id = getattr(self.request, 'tenant_id', '')
        return Patient.objects.filter(
            tenant_id=tenant_id
        ).select_related(
            'attending_physician',
            'created_by',
        ).prefetch_related(
            'allergy_records',
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PatientListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PatientCreateSerializer
        return PatientSerializer

    def get_permissions(self):
        """Set required permission based on action."""
        permission_map = {
            'create': 'healthcare.patient.create',
            'update': 'healthcare.patient.update',
            'partial_update': 'healthcare.patient.update',
            'destroy': 'healthcare.patient.delete',
            'admit': 'healthcare.patient.admit',
            'discharge': 'healthcare.patient.discharge',
        }
        self.required_permission = permission_map.get(
            self.action, 'healthcare.patient.read'
        )
        return super().get_permissions()

    def perform_destroy(self, instance):
        """Soft delete - mark as inactive instead of deleting."""
        instance.status = Patient.Status.DISCHARGED
        instance.modified_by = self.request.user
        instance.save(update_fields=['status', 'modified_by', 'updated_at'])

    @action(detail=True, methods=['post'])
    def admit(self, request, pk=None):
        """Admit a patient to a ward."""
        patient = self.get_object()

        if patient.status == Patient.Status.ACTIVE and patient.admission_date:
            return Response(
                {'error': 'Patient is already admitted.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PatientAdmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        patient.status = Patient.Status.ACTIVE
        patient.ward = serializer.validated_data['ward']
        patient.bed_number = serializer.validated_data.get('bed_number', '')
        patient.attending_physician = serializer.validated_data.get('attending_physician')
        patient.admission_date = timezone.now()
        patient.discharge_date = None
        patient.modified_by = request.user
        patient.save()

        return Response({
            'message': f'Patient {patient.full_name} admitted to {patient.ward}',
            'patient': PatientSerializer(patient).data
        })

    @action(detail=True, methods=['post'])
    def discharge(self, request, pk=None):
        """Discharge a patient."""
        patient = self.get_object()

        if patient.status != Patient.Status.ACTIVE:
            return Response(
                {'error': 'Patient is not currently admitted.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PatientDischargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        patient.status = Patient.Status.DISCHARGED
        patient.discharge_date = timezone.now()
        patient.ward = ''
        patient.bed_number = ''
        patient.modified_by = request.user
        patient.save()

        return Response({
            'message': f'Patient {patient.full_name} discharged',
            'patient': PatientSerializer(patient).data
        })

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search patients by multiple criteria.

        Query params:
            q: Search term (searches name, patient_number, MRN)
            wristband: Wristband barcode
        """
        q = request.query_params.get('q', '')
        wristband = request.query_params.get('wristband', '')

        queryset = self.get_queryset()

        if wristband:
            queryset = queryset.filter(wristband_id=wristband)
        elif q:
            queryset = queryset.filter(
                Q(patient_number__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(medical_record_number__icontains=q)
            )
        else:
            return Response(
                {'error': 'Search query (q) or wristband required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PatientListSerializer(queryset[:20], many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def allergies(self, request, pk=None):
        """Get all allergies for a patient."""
        patient = self.get_object()
        allergies = patient.allergy_records.all()
        serializer = PatientAllergySerializer(allergies, many=True)
        return Response(serializer.data)


class PatientAllergyViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """
    ViewSet for Patient Allergies.

    Nested under patients: /api/v1/healthcare/patients/{patient_id}/allergies/
    """

    serializer_class = PatientAllergySerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'healthcare.patient.read'

    def get_queryset(self):
        """Filter allergies by patient."""
        patient_id = self.kwargs.get('patient_pk')
        return PatientAllergy.objects.filter(
            patient_id=patient_id
        ).select_related('verified_by')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.required_permission = 'healthcare.patient.update'
        return super().get_permissions()

    def perform_create(self, serializer):
        patient_id = self.kwargs.get('patient_pk')
        serializer.save(
            patient_id=patient_id,
            created_by=self.request.user
        )

    @action(detail=True, methods=['post'])
    def verify(self, request, patient_pk=None, pk=None):
        """Verify an allergy record."""
        allergy = self.get_object()

        if allergy.verified:
            return Response(
                {'error': 'Allergy already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        allergy.verified = True
        allergy.verified_by = request.user
        allergy.save(update_fields=['verified', 'verified_by', 'updated_at'])

        return Response({
            'message': 'Allergy verified',
            'allergy': PatientAllergySerializer(allergy).data
        })
