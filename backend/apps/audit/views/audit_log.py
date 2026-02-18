"""
Audit log views (read-only).
"""
from datetime import datetime, timezone
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.audit.serializers.audit_log import AuditIntegrityReportSerializer
from apps.iam.permissions import RBACPermission


class AuditLogFilter(filters.FilterSet):
    """Filter for audit logs."""

    start_date = filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    end_date = filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    user_email = filters.CharFilter(lookup_expr='icontains')
    record_identifier = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = AuditLog
        fields = [
            'action',
            'record_type',
            'user',
            'user_email',
            'record_identifier',
            'start_date',
            'end_date',
        ]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs (read-only).

    GET /api/v1/audit/logs/ - List audit logs
    GET /api/v1/audit/logs/{id}/ - Get audit log entry

    Supports filtering by:
    - action: Filter by action type
    - record_type: Filter by record type
    - user: Filter by user ID
    - user_email: Filter by user email (partial match)
    - record_identifier: Filter by record identifier
    - start_date: Filter from date
    - end_date: Filter to date
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'audit.log.read'
    filterset_class = AuditLogFilter
    search_fields = ['user_email', 'action_description', 'record_identifier']
    ordering_fields = ['timestamp', 'sequence_number', 'action']
    ordering = ['-timestamp']


class AuditIntegrityView(APIView):
    """
    Verify audit trail integrity.

    GET /api/v1/audit/integrity/

    Returns integrity verification results for the audit chain.
    FDA 21 CFR Part 11 compliance requirement.
    """
    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'audit.integrity.verify'

    def get(self, request):
        """Verify audit chain integrity."""
        # Get optional sequence range
        start_sequence = request.query_params.get('start_sequence')
        end_sequence = request.query_params.get('end_sequence')

        if start_sequence:
            start_sequence = int(start_sequence)
        if end_sequence:
            end_sequence = int(end_sequence)

        # Verify chain
        issues = AuditLog.verify_chain_integrity(
            start_sequence=start_sequence,
            end_sequence=end_sequence
        )

        # Get entry count
        queryset = AuditLog.objects.all()
        if start_sequence:
            queryset = queryset.filter(sequence_number__gte=start_sequence)
        if end_sequence:
            queryset = queryset.filter(sequence_number__lte=end_sequence)
        entries_checked = queryset.count()

        report_data = {
            'is_valid': len(issues) == 0,
            'entries_checked': entries_checked,
            'issues_found': len(issues),
            'issues': issues,
            'verification_timestamp': datetime.now(timezone.utc)
        }

        serializer = AuditIntegrityReportSerializer(report_data)
        return Response(serializer.data)
