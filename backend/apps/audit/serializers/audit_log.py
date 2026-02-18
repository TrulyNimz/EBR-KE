"""
Audit log serializers.
"""
from rest_framework import serializers
from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit log entries (read-only)."""

    user_display = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'timestamp',
            'user',
            'user_email',
            'user_full_name',
            'user_display',
            'action',
            'action_display',
            'action_description',
            'record_type',
            'record_identifier',
            'object_id',
            'old_values',
            'new_values',
            'changed_fields',
            'ip_address',
            'request_id',
            'entry_hash',
            'sequence_number',
        ]
        read_only_fields = fields

    def get_user_display(self, obj):
        """Get formatted user display name."""
        if obj.user_full_name:
            return f'{obj.user_full_name} ({obj.user_email})'
        return obj.user_email


class AuditLogExportSerializer(serializers.ModelSerializer):
    """Serializer for audit log export (FDA compliance reports)."""

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'timestamp',
            'user_email',
            'user_full_name',
            'action',
            'action_description',
            'record_type',
            'record_identifier',
            'object_id',
            'old_values',
            'new_values',
            'changed_fields',
            'ip_address',
            'user_agent',
            'tenant_id',
            'entry_hash',
            'previous_hash',
            'sequence_number',
        ]


class AuditIntegrityReportSerializer(serializers.Serializer):
    """Serializer for audit chain integrity verification results."""

    is_valid = serializers.BooleanField()
    entries_checked = serializers.IntegerField()
    issues_found = serializers.IntegerField()
    issues = serializers.ListField(child=serializers.DictField())
    verification_timestamp = serializers.DateTimeField()
