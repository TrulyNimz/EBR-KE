"""
Digital signature views.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.contrib.contenttypes.models import ContentType

from apps.audit.models import SignatureMeaning, DigitalSignature, SignatureRequirement
from apps.audit.serializers import (
    SignatureMeaningSerializer,
    DigitalSignatureSerializer,
    SignatureCreateSerializer,
    SignatureRequirementSerializer,
)
from apps.audit.serializers.signatures import SignatureStatusSerializer
from apps.audit.middleware import get_audit_context
from apps.iam.permissions import RBACPermission


class SignatureMeaningViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for signature meanings (read-only).

    GET /api/v1/audit/signature-meanings/
    """
    queryset = SignatureMeaning.objects.filter(is_active=True)
    serializer_class = SignatureMeaningSerializer
    permission_classes = [IsAuthenticated]


class DigitalSignatureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for digital signatures.

    GET /api/v1/audit/signatures/ - List signatures
    GET /api/v1/audit/signatures/{id}/ - Get signature details
    POST /api/v1/audit/signatures/{id}/verify/ - Verify a signature
    """
    queryset = DigitalSignature.objects.all()
    serializer_class = DigitalSignatureSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'audit.signature.read'
    filterset_fields = ['signer', 'meaning', 'record_type', 'status']
    search_fields = ['signer_email', 'record_identifier']
    ordering = ['-signed_at']

    @action(detail=True, methods=['get'])
    def verify(self, request, pk=None):
        """Verify a specific signature."""
        signature = self.get_object()
        is_valid = signature.verify()

        return Response({
            'signature_id': str(signature.id),
            'is_valid': is_valid,
            'signer': signature.signer_email,
            'meaning': signature.meaning.name,
            'signed_at': signature.signed_at,
            'status': signature.status,
        })

    @action(detail=False, methods=['get'])
    def for_record(self, request):
        """
        Get all signatures for a specific record.

        Query params:
        - record_type: The model name (e.g., 'batchrecord')
        - record_id: The record's primary key
        """
        record_type = request.query_params.get('record_type')
        record_id = request.query_params.get('record_id')

        if not record_type or not record_id:
            return Response(
                {'error': 'record_type and record_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            content_type = ContentType.objects.get(model=record_type)
        except ContentType.DoesNotExist:
            return Response(
                {'error': f'Unknown record type: {record_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        signatures = DigitalSignature.objects.filter(
            content_type=content_type,
            object_id=str(record_id)
        ).select_related('meaning', 'signer')

        # Check requirements
        is_complete, missing = SignatureRequirement.check_requirements_by_type(
            record_type, record_id
        ) if hasattr(SignatureRequirement, 'check_requirements_by_type') else (True, [])

        response_data = {
            'is_complete': is_complete,
            'total_required': len(missing) + signatures.filter(
                status=DigitalSignature.Status.VALID
            ).count(),
            'total_collected': signatures.filter(
                status=DigitalSignature.Status.VALID
            ).count(),
            'missing_requirements': missing,
            'signatures': DigitalSignatureSerializer(signatures, many=True).data
        }

        return Response(response_data)


class SignatureRequirementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for signature requirements.

    Manages which signatures are required for different record types.
    """
    queryset = SignatureRequirement.objects.all()
    serializer_class = SignatureRequirementSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'audit.requirement.read'
    filterset_fields = ['record_type', 'workflow_state', 'is_active']
    ordering = ['record_type', 'order']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.required_permission = 'audit.requirement.manage'
        return super().get_permissions()
