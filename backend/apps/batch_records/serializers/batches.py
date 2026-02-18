"""
Batch Records serializers.
"""
from rest_framework import serializers
from apps.batch_records.models import (
    Batch,
    BatchTemplate,
    BatchStep,
    BatchStepTemplate,
    BatchAttachment,
)


class BatchStepSerializer(serializers.ModelSerializer):
    """Serializer for batch steps."""

    executed_by_name = serializers.CharField(
        source='executed_by.full_name',
        read_only=True
    )
    verified_by_name = serializers.CharField(
        source='verified_by.full_name',
        read_only=True
    )
    can_start = serializers.BooleanField(read_only=True)
    # Surface template signature requirements onto the step so the frontend
    # doesn't need to separately fetch templates.
    requires_signature = serializers.SerializerMethodField()
    signature_meaning = serializers.SerializerMethodField()

    class Meta:
        model = BatchStep
        fields = [
            'id',
            'code',
            'name',
            'description',
            'instructions',
            'sequence',
            'step_type',
            'status',
            'form_schema',
            'data',
            'started_at',
            'completed_at',
            'executed_by',
            'executed_by_name',
            'verified_by',
            'verified_by_name',
            'verified_at',
            'has_deviation',
            'deviation_notes',
            'requires_signature',
            'signature_meaning',
            'can_start',
            'created_at',
            'modified_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'modified_at', 'started_at', 'completed_at',
            'executed_by', 'verified_by', 'verified_at'
        ]

    def get_requires_signature(self, obj):
        if obj.template:
            return obj.template.requires_signature
        return False

    def get_signature_meaning(self, obj):
        if obj.template:
            return obj.template.signature_meaning or ''
        return ''


class BatchStepExecuteSerializer(serializers.Serializer):
    """Serializer for executing a batch step."""

    data = serializers.JSONField(required=False, default=dict)
    has_deviation = serializers.BooleanField(required=False, default=False)
    deviation_notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        step = self.context.get('step')
        if not step or not step.form_schema:
            return attrs

        schema = step.form_schema
        submitted_data = attrs.get('data', {})
        errors = {}

        # Validate required fields
        required_fields = schema.get('required', [])
        for field_name in required_fields:
            if field_name not in submitted_data or submitted_data[field_name] in (None, '', []):
                errors[field_name] = f'This field is required.'

        # Validate field types and constraints
        properties = schema.get('properties', {})
        for field_name, field_schema in properties.items():
            value = submitted_data.get(field_name)
            if value is None:
                continue  # Required check already handled above

            field_type = field_schema.get('type')

            if field_type in ('number', 'integer'):
                try:
                    num_value = float(value)
                    if field_type == 'integer' and not float(value).is_integer():
                        errors[field_name] = 'Must be an integer.'
                    minimum = field_schema.get('minimum')
                    maximum = field_schema.get('maximum')
                    if minimum is not None and num_value < minimum:
                        errors[field_name] = f'Must be at least {minimum}.'
                    elif maximum is not None and num_value > maximum:
                        errors[field_name] = f'Must be at most {maximum}.'
                except (TypeError, ValueError):
                    errors[field_name] = 'Must be a number.'

            elif field_type == 'string':
                enum_values = field_schema.get('enum')
                if enum_values and value not in enum_values:
                    errors[field_name] = f'Must be one of: {", ".join(enum_values)}.'
                min_length = field_schema.get('minLength')
                max_length = field_schema.get('maxLength')
                if min_length and len(str(value)) < min_length:
                    errors[field_name] = f'Must be at least {min_length} characters.'
                elif max_length and len(str(value)) > max_length:
                    errors[field_name] = f'Must be at most {max_length} characters.'

            elif field_type == 'boolean':
                if not isinstance(value, bool):
                    errors[field_name] = 'Must be true or false.'

        if errors:
            raise serializers.ValidationError({'data': errors})

        return attrs


class BatchAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for batch attachments."""

    uploaded_by = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = BatchAttachment
        fields = [
            'id',
            'batch',
            'step',
            'file',
            'filename',
            'file_size',
            'content_type',
            'attachment_type',
            'title',
            'description',
            'version',
            'file_hash',
            'uploaded_by',
            'created_at',
        ]
        read_only_fields = ['id', 'file_size', 'file_hash', 'created_at']


class BatchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for batch lists."""

    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    completion_percentage = serializers.IntegerField(read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = [
            'id',
            'batch_number',
            'name',
            'product_code',
            'product_name',
            'status',
            'priority',
            'module_type',
            'completion_percentage',
            'step_count',
            'scheduled_start',
            'actual_start',
            'created_by_name',
            'created_at',
        ]

    def get_step_count(self, obj):
        return obj.steps.count()


class BatchSerializer(serializers.ModelSerializer):
    """Full serializer for batch details."""

    steps = BatchStepSerializer(many=True, read_only=True)
    attachments = BatchAttachmentSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    modified_by_name = serializers.CharField(
        source='modified_by.full_name',
        read_only=True,
        allow_null=True
    )
    completion_percentage = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    integrity_valid = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = [
            'id',
            'batch_number',
            'name',
            'description',
            'product_code',
            'product_name',
            'template',
            'status',
            'priority',
            'module_type',
            'workflow_instance',
            'scheduled_start',
            'scheduled_end',
            'actual_start',
            'actual_end',
            'planned_quantity',
            'actual_quantity',
            'quantity_unit',
            'custom_data',
            'completion_percentage',
            'is_complete',
            'integrity_valid',
            'steps',
            'attachments',
            'created_by',
            'created_by_name',
            'modified_by',
            'modified_by_name',
            'created_at',
            'modified_at',
            'record_checksum',
            'version',
        ]
        read_only_fields = [
            'id', 'created_at', 'modified_at', 'created_by', 'modified_by',
            'record_checksum', 'version', 'actual_start', 'actual_end'
        ]

    def get_integrity_valid(self, obj):
        return obj.verify_integrity()


class BatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating batches."""

    class Meta:
        model = Batch
        fields = [
            'batch_number',
            'name',
            'description',
            'product_code',
            'product_name',
            'template',
            'priority',
            'module_type',
            'scheduled_start',
            'scheduled_end',
            'planned_quantity',
            'quantity_unit',
            'custom_data',
        ]

    def validate_batch_number(self, value):
        if Batch.objects.filter(batch_number=value).exists():
            raise serializers.ValidationError('Batch number already exists.')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        # If template provided, use it to create the batch
        template = validated_data.pop('template', None)
        if template:
            batch_number = validated_data.pop('batch_number')
            return template.create_batch(user, batch_number, **validated_data)

        # Otherwise create batch directly
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        return super().create(validated_data)


class BatchStepTemplateSerializer(serializers.ModelSerializer):
    """Serializer for batch step templates."""

    class Meta:
        model = BatchStepTemplate
        fields = [
            'id',
            'code',
            'name',
            'description',
            'instructions',
            'sequence',
            'step_type',
            'form_schema',
            'requires_verification',
            'requires_signature',
            'signature_meaning',
            'required_role',
            'verifier_role',
            'workflow_state',
            'default_data',
        ]


class BatchTemplateSerializer(serializers.ModelSerializer):
    """Serializer for batch templates."""

    step_templates = BatchStepTemplateSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = BatchTemplate
        fields = [
            'id',
            'code',
            'name',
            'description',
            'version',
            'status',
            'product_code',
            'product_name',
            'workflow',
            'module_type',
            'default_quantity_unit',
            'default_custom_data',
            'step_templates',
            'created_by',
            'created_by_name',
            'created_at',
            'modified_at',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'modified_at', 'created_by']
