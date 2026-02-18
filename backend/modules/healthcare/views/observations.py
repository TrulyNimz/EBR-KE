"""
Clinical observation views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import models

from modules.healthcare.models import VitalSigns, ClinicalNote, Assessment
from modules.healthcare.serializers import (
    VitalSignsSerializer,
    VitalSignsCreateSerializer,
    ClinicalNoteSerializer,
    ClinicalNoteCreateSerializer,
    AssessmentSerializer,
)
from modules.healthcare.serializers.observations import (
    AssessmentCreateSerializer,
    ClinicalNoteSignSerializer,
)
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class VitalSignsViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """
    ViewSet for Vital Signs recording and retrieval.

    Endpoints:
        GET  /api/v1/healthcare/vital-signs/           - List vital signs
        POST /api/v1/healthcare/vital-signs/           - Record vital signs
        GET  /api/v1/healthcare/vital-signs/{id}/      - Get record
        GET  /api/v1/healthcare/vital-signs/latest/    - Get latest for patient
        GET  /api/v1/healthcare/vital-signs/trends/    - Get trends for patient
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'healthcare.vitals.read'
    http_method_names = ['get', 'post', 'head', 'options']  # Vitals are immutable
    filterset_fields = ['patient', 'recorded_by']
    ordering = ['-recorded_at']

    def get_queryset(self):
        """Filter by tenant."""
        tenant_id = getattr(self.request, 'tenant_id', '')
        return VitalSigns.objects.filter(
            tenant_id=tenant_id
        ).select_related('patient', 'recorded_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return VitalSignsCreateSerializer
        return VitalSignsSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'healthcare.vitals.record'
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest vital signs for a patient."""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id query parameter required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        vitals = self.get_queryset().filter(
            patient_id=patient_id
        ).first()

        if not vitals:
            return Response(
                {'error': 'No vital signs found for patient.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = VitalSignsSerializer(vitals)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def trends(self, request):
        """
        Get vital signs trends for a patient.

        Returns aggregated data for charting.

        Query params:
            patient_id: Required
            days: Number of days to include (default: 7)
            vital: Specific vital to trend (optional)
        """
        patient_id = request.query_params.get('patient_id')
        days = int(request.query_params.get('days', 7))
        vital_type = request.query_params.get('vital')

        if not patient_id:
            return Response(
                {'error': 'patient_id query parameter required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cutoff = timezone.now() - timezone.timedelta(days=days)
        vitals = self.get_queryset().filter(
            patient_id=patient_id,
            recorded_at__gte=cutoff
        ).order_by('recorded_at')

        # Build trend data
        trends = {
            'temperature': [],
            'pulse': [],
            'respiratory_rate': [],
            'blood_pressure_systolic': [],
            'blood_pressure_diastolic': [],
            'oxygen_saturation': [],
        }

        for v in vitals:
            timestamp = v.recorded_at.isoformat()
            if v.temperature:
                trends['temperature'].append({'time': timestamp, 'value': float(v.temperature)})
            if v.pulse:
                trends['pulse'].append({'time': timestamp, 'value': v.pulse})
            if v.respiratory_rate:
                trends['respiratory_rate'].append({'time': timestamp, 'value': v.respiratory_rate})
            if v.blood_pressure_systolic:
                trends['blood_pressure_systolic'].append({'time': timestamp, 'value': v.blood_pressure_systolic})
            if v.blood_pressure_diastolic:
                trends['blood_pressure_diastolic'].append({'time': timestamp, 'value': v.blood_pressure_diastolic})
            if v.oxygen_saturation:
                trends['oxygen_saturation'].append({'time': timestamp, 'value': float(v.oxygen_saturation)})

        if vital_type and vital_type in trends:
            return Response({vital_type: trends[vital_type]})

        return Response(trends)

    @action(detail=False, methods=['get'])
    def abnormal(self, request):
        """Get recent abnormal vital signs for alerting."""
        hours = int(request.query_params.get('hours', 24))
        ward = request.query_params.get('ward')

        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        queryset = self.get_queryset().filter(recorded_at__gte=cutoff)

        if ward:
            queryset = queryset.filter(patient__ward=ward)

        # Filter for abnormal values
        abnormal_vitals = queryset.filter(
            models.Q(temperature__lt=36.1) | models.Q(temperature__gt=37.2) |
            models.Q(pulse__lt=60) | models.Q(pulse__gt=100) |
            models.Q(respiratory_rate__lt=12) | models.Q(respiratory_rate__gt=20) |
            models.Q(blood_pressure_systolic__gte=140) | models.Q(blood_pressure_systolic__lt=90) |
            models.Q(blood_pressure_diastolic__gte=90) | models.Q(blood_pressure_diastolic__lt=60) |
            models.Q(oxygen_saturation__lt=95)
        )[:50]

        serializer = VitalSignsSerializer(abnormal_vitals, many=True)
        return Response(serializer.data)


class ClinicalNoteViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """
    ViewSet for Clinical Notes.

    Endpoints:
        GET    /api/v1/healthcare/clinical-notes/           - List notes
        POST   /api/v1/healthcare/clinical-notes/           - Create note
        GET    /api/v1/healthcare/clinical-notes/{id}/      - Get note
        PATCH  /api/v1/healthcare/clinical-notes/{id}/      - Update draft note
        POST   /api/v1/healthcare/clinical-notes/{id}/sign/ - Sign note
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'healthcare.notes.read'
    filterset_fields = ['patient', 'note_type', 'status', 'author', 'is_confidential']
    search_fields = ['title', 'content']
    ordering = ['-authored_at']

    def get_queryset(self):
        """Filter by tenant, hide confidential notes from non-authorized users."""
        tenant_id = getattr(self.request, 'tenant_id', '')
        queryset = ClinicalNote.objects.filter(
            tenant_id=tenant_id
        ).select_related('patient', 'author', 'cosigned_by')

        # Filter confidential notes unless user has special permission
        user = self.request.user
        if not user.has_permission('healthcare.notes.view_confidential'):
            queryset = queryset.filter(
                models.Q(is_confidential=False) | models.Q(author=user)
            )

        return queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClinicalNoteCreateSerializer
        return ClinicalNoteSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'healthcare.notes.create',
            'update': 'healthcare.notes.update',
            'partial_update': 'healthcare.notes.update',
            'destroy': 'healthcare.notes.delete',
            'sign': 'healthcare.notes.sign',
        }
        self.required_permission = permission_map.get(
            self.action, 'healthcare.notes.read'
        )
        return super().get_permissions()

    def perform_update(self, serializer):
        """Only allow updates to draft notes."""
        instance = self.get_object()
        if instance.status != ClinicalNote.Status.DRAFT:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Cannot edit a signed note.')

        if instance.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the author can edit this note.')

        serializer.save(modified_by=self.request.user)

    def perform_destroy(self, instance):
        """Only allow deletion of draft notes by author."""
        if instance.status != ClinicalNote.Status.DRAFT:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Cannot delete a signed note.')

        if instance.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the author can delete this note.')

        instance.delete()

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """Sign or co-sign a clinical note."""
        note = self.get_object()

        serializer = ClinicalNoteSignSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        action_type = serializer.validated_data['action']

        if action_type == 'sign':
            if note.status != ClinicalNote.Status.DRAFT:
                return Response(
                    {'error': 'Note is already signed.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if note.author != request.user:
                return Response(
                    {'error': 'Only the author can sign this note.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            note.status = ClinicalNote.Status.SIGNED
            note.save(update_fields=['status', 'updated_at'])

            return Response({
                'message': 'Note signed successfully',
                'note': ClinicalNoteSerializer(note).data
            })

        elif action_type == 'cosign':
            if note.status != ClinicalNote.Status.SIGNED:
                return Response(
                    {'error': 'Note must be signed before co-signing.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if note.cosigned_by:
                return Response(
                    {'error': 'Note already co-signed.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if note.author == request.user:
                return Response(
                    {'error': 'Author cannot co-sign their own note.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            note.cosigned_by = request.user
            note.cosigned_at = timezone.now()
            note.status = ClinicalNote.Status.COSIGNED
            note.save(update_fields=['cosigned_by', 'cosigned_at', 'status', 'updated_at'])

            return Response({
                'message': 'Note co-signed successfully',
                'note': ClinicalNoteSerializer(note).data
            })


class AssessmentViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """
    ViewSet for Patient Assessments.

    Endpoints:
        GET    /api/v1/healthcare/assessments/           - List assessments
        POST   /api/v1/healthcare/assessments/           - Create assessment
        GET    /api/v1/healthcare/assessments/{id}/      - Get assessment
        PATCH  /api/v1/healthcare/assessments/{id}/      - Update assessment
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'healthcare.assessment.read'
    filterset_fields = ['patient', 'assessment_type', 'risk_level', 'assessed_by']
    ordering = ['-assessment_date']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return Assessment.objects.filter(
            tenant_id=tenant_id
        ).select_related('patient', 'assessed_by')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AssessmentCreateSerializer
        return AssessmentSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'healthcare.assessment.create',
            'update': 'healthcare.assessment.update',
            'partial_update': 'healthcare.assessment.update',
            'destroy': 'healthcare.assessment.delete',
        }
        self.required_permission = permission_map.get(
            self.action, 'healthcare.assessment.read'
        )
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def high_risk(self, request):
        """Get patients with high-risk assessments."""
        queryset = self.get_queryset().filter(
            risk_level__in=['high', 'critical']
        ).select_related('patient')

        # Get only the latest assessment per patient
        from django.db.models import Max
        latest_per_patient = queryset.values('patient').annotate(
            latest=Max('assessment_date')
        )

        patient_latest = {
            item['patient']: item['latest']
            for item in latest_per_patient
        }

        # Filter to only latest
        result = [
            a for a in queryset
            if a.assessment_date == patient_latest.get(a.patient_id)
        ]

        serializer = AssessmentSerializer(result, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def follow_ups_due(self, request):
        """Get assessments with follow-ups due."""
        today = timezone.now().date()
        days_ahead = int(request.query_params.get('days', 7))
        end_date = today + timezone.timedelta(days=days_ahead)

        queryset = self.get_queryset().filter(
            follow_up_required=True,
            follow_up_date__gte=today,
            follow_up_date__lte=end_date
        ).order_by('follow_up_date')

        serializer = AssessmentSerializer(queryset, many=True)
        return Response(serializer.data)
