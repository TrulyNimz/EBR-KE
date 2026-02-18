"""
Traceability serializers.
"""
from rest_framework import serializers
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from modules.agriculture.models import TraceabilityRecord, CertificationRecord


class TraceabilityRecordSerializer(serializers.ModelSerializer):
    """Traceability record serializer."""

    handled_by_name = serializers.CharField(source='handled_by.full_name', read_only=True)
    verified_by_name = serializers.CharField(
        source='verified_by.full_name',
        read_only=True,
        allow_null=True
    )
    chain = serializers.SerializerMethodField()

    class Meta:
        model = TraceabilityRecord
        fields = [
            'id',
            'trace_code',
            'content_type',
            'object_id',
            'event_type',
            'event_date',
            'event_location',
            'latitude',
            'longitude',
            'product_description',
            'quantity',
            'unit',
            'quality_grade',
            'quality_parameters',
            'previous_record',
            'from_party',
            'to_party',
            'certifications',
            'documents',
            'handled_by',
            'handled_by_name',
            'verified',
            'verified_by',
            'verified_by_name',
            'verified_at',
            'blockchain_hash',
            'notes',
            'chain',
            'created_at',
        ]
        read_only_fields = [
            'id', 'trace_code', 'created_at', 'handled_by',
            'verified', 'verified_by', 'verified_at', 'blockchain_hash',
        ]

    def get_chain(self, obj):
        """Get simplified chain history."""
        chain = obj.get_full_chain()
        return [
            {
                'trace_code': r.trace_code,
                'event_type': r.event_type,
                'event_date': r.event_date,
                'event_location': r.event_location,
                'from_party': r.from_party,
                'to_party': r.to_party,
            }
            for r in chain
        ]


class TraceabilityRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating traceability records."""

    source_type = serializers.CharField(write_only=True)
    source_id = serializers.CharField(write_only=True)

    class Meta:
        model = TraceabilityRecord
        fields = [
            'source_type',
            'source_id',
            'event_type',
            'event_date',
            'event_location',
            'latitude',
            'longitude',
            'product_description',
            'quantity',
            'unit',
            'quality_grade',
            'quality_parameters',
            'previous_record',
            'from_party',
            'to_party',
            'certifications',
            'documents',
            'notes',
        ]

    def validate(self, attrs):
        source_type = attrs.pop('source_type')
        source_id = attrs.pop('source_id')

        # Get content type
        try:
            app_label, model = source_type.lower().split('.')
            content_type = ContentType.objects.get(app_label=app_label, model=model)
        except (ValueError, ContentType.DoesNotExist):
            raise serializers.ValidationError({
                'source_type': f'Invalid source type: {source_type}'
            })

        attrs['content_type'] = content_type
        attrs['object_id'] = source_id

        # Validate previous record creates valid chain
        if attrs.get('previous_record'):
            prev = attrs['previous_record']
            if prev.content_type != content_type or prev.object_id != source_id:
                raise serializers.ValidationError({
                    'previous_record': 'Previous record must be for the same source object.'
                })

        return attrs

    def create(self, validated_data):
        import uuid
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        validated_data['trace_code'] = f"TR-{uuid.uuid4().hex[:12].upper()}"
        validated_data['handled_by'] = user
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id

        return super().create(validated_data)


class CertificationRecordSerializer(serializers.ModelSerializer):
    """Certification record serializer."""

    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = CertificationRecord
        fields = [
            'id',
            'certification_type',
            'certification_name',
            'certifying_body',
            'certificate_number',
            'issued_date',
            'expiry_date',
            'is_valid',
            'is_expired',
            'days_until_expiry',
            'scope_description',
            'certificate_file',
            'content_type',
            'object_id',
            'last_audit_date',
            'next_audit_date',
            'audit_notes',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class CertificationRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating certification records."""

    entity_type = serializers.CharField(write_only=True)
    entity_id = serializers.CharField(write_only=True)

    class Meta:
        model = CertificationRecord
        fields = [
            'entity_type',
            'entity_id',
            'certification_type',
            'certification_name',
            'certifying_body',
            'certificate_number',
            'issued_date',
            'expiry_date',
            'scope_description',
            'certificate_file',
            'last_audit_date',
            'next_audit_date',
            'audit_notes',
        ]

    def validate(self, attrs):
        entity_type = attrs.pop('entity_type')
        entity_id = attrs.pop('entity_id')

        # Get content type
        try:
            app_label, model = entity_type.lower().split('.')
            content_type = ContentType.objects.get(app_label=app_label, model=model)
        except (ValueError, ContentType.DoesNotExist):
            raise serializers.ValidationError({
                'entity_type': f'Invalid entity type: {entity_type}'
            })

        attrs['content_type'] = content_type
        attrs['object_id'] = entity_id

        # Validate dates
        if attrs.get('expiry_date') and attrs.get('issued_date'):
            if attrs['expiry_date'] <= attrs['issued_date']:
                raise serializers.ValidationError({
                    'expiry_date': 'Expiry date must be after issued date.'
                })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        return super().create(validated_data)
