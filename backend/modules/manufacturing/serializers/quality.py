"""
Quality control serializers.
"""
from rest_framework import serializers
from django.utils import timezone
from modules.manufacturing.models import (
    QCTest,
    QCTestRequest,
    QCResult,
    BatchRelease,
)


class QCTestSerializer(serializers.ModelSerializer):
    """QC test definition serializer."""

    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = QCTest
        fields = [
            'id',
            'code',
            'name',
            'description',
            'test_type',
            'method_reference',
            'method_description',
            'specification',
            'result_type',
            'unit_of_measure',
            'typical_duration_hours',
            'is_active',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def validate_code(self, value):
        return value.upper()

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        return super().create(validated_data)


class QCResultSerializer(serializers.ModelSerializer):
    """QC result serializer."""

    test_name = serializers.CharField(source='test.name', read_only=True)
    test_code = serializers.CharField(source='test.code', read_only=True)
    tested_by_name = serializers.CharField(source='tested_by.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = QCResult
        fields = [
            'id',
            'request',
            'test',
            'test_name',
            'test_code',
            'result_value',
            'result_numeric',
            'result_unit',
            'result_data',
            'outcome',
            'specification_used',
            'within_specification',
            'tested_by',
            'tested_by_name',
            'tested_at',
            'reviewed_by',
            'reviewed_by_name',
            'reviewed_at',
            'is_retest',
            'retest_reason',
            'original_result',
            'notes',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'tested_by', 'reviewed_by', 'reviewed_at',
        ]


class QCResultCreateSerializer(serializers.ModelSerializer):
    """Serializer for recording QC results."""

    class Meta:
        model = QCResult
        fields = [
            'request',
            'test',
            'result_value',
            'result_numeric',
            'result_unit',
            'result_data',
            'is_retest',
            'retest_reason',
            'original_result',
            'notes',
        ]

    def validate(self, attrs):
        """Validate QC result."""
        test = attrs.get('test')
        request = attrs.get('request')

        # Verify test is part of the request
        if test not in request.tests.all():
            raise serializers.ValidationError({
                'test': 'Test is not part of this QC request.'
            })

        # If retest, require reason and original
        if attrs.get('is_retest'):
            if not attrs.get('retest_reason'):
                raise serializers.ValidationError({
                    'retest_reason': 'Retest reason required.'
                })
            if not attrs.get('original_result'):
                raise serializers.ValidationError({
                    'original_result': 'Original result reference required for retest.'
                })

        # Evaluate specification compliance
        spec = test.specification
        result_numeric = attrs.get('result_numeric')

        if result_numeric is not None and spec:
            within_spec = True
            if 'min' in spec and result_numeric < spec['min']:
                within_spec = False
            if 'max' in spec and result_numeric > spec['max']:
                within_spec = False
            attrs['within_specification'] = within_spec
            attrs['specification_used'] = spec

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['tested_by'] = user
        validated_data['tested_at'] = timezone.now()
        validated_data['created_by'] = user

        # Determine outcome based on specification
        if validated_data.get('within_specification') is True:
            validated_data['outcome'] = QCResult.Outcome.PASS
        elif validated_data.get('within_specification') is False:
            validated_data['outcome'] = QCResult.Outcome.FAIL
        else:
            validated_data['outcome'] = QCResult.Outcome.PENDING

        return super().create(validated_data)


class QCTestRequestSerializer(serializers.ModelSerializer):
    """QC test request serializer."""

    batch_number = serializers.CharField(source='batch.batch_number', read_only=True, allow_null=True)
    lot_number = serializers.CharField(source='material_lot.internal_lot_number', read_only=True, allow_null=True)
    requested_by_name = serializers.CharField(source='requested_by.full_name', read_only=True)
    test_names = serializers.SerializerMethodField()
    results = QCResultSerializer(many=True, read_only=True)
    completion_percentage = serializers.SerializerMethodField()

    class Meta:
        model = QCTestRequest
        fields = [
            'id',
            'request_number',
            'sample_type',
            'sample_description',
            'sample_quantity',
            'batch',
            'batch_number',
            'material_lot',
            'lot_number',
            'tests',
            'test_names',
            'status',
            'requested_by',
            'requested_by_name',
            'requested_at',
            'priority',
            'due_date',
            'completed_at',
            'results',
            'completion_percentage',
            'notes',
            'created_at',
        ]
        read_only_fields = [
            'id', 'request_number', 'created_at', 'requested_by', 'requested_at',
            'completed_at',
        ]

    def get_test_names(self, obj):
        return list(obj.tests.values_list('name', flat=True))

    def get_completion_percentage(self, obj):
        total_tests = obj.tests.count()
        if total_tests == 0:
            return 0
        completed = obj.results.exclude(outcome=QCResult.Outcome.PENDING).count()
        return int((completed / total_tests) * 100)


class QCTestRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating QC test requests."""

    class Meta:
        model = QCTestRequest
        fields = [
            'sample_type',
            'sample_description',
            'sample_quantity',
            'batch',
            'material_lot',
            'tests',
            'priority',
            'due_date',
            'notes',
        ]

    def validate(self, attrs):
        """Validate test request."""
        # Must have either batch or material_lot
        if not attrs.get('batch') and not attrs.get('material_lot'):
            raise serializers.ValidationError(
                'Either batch or material_lot must be specified.'
            )

        # Must have at least one test
        if not attrs.get('tests'):
            raise serializers.ValidationError({
                'tests': 'At least one test must be selected.'
            })

        return attrs

    def create(self, validated_data):
        import uuid
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        tests = validated_data.pop('tests', [])
        validated_data['request_number'] = f"QC-{uuid.uuid4().hex[:8].upper()}"
        validated_data['requested_by'] = user
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id

        instance = super().create(validated_data)
        instance.tests.set(tests)
        return instance


class BatchReleaseSerializer(serializers.ModelSerializer):
    """Batch release serializer."""

    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    product_name = serializers.CharField(source='batch.product_name', read_only=True)
    decision_by_name = serializers.CharField(source='decision_by.full_name', read_only=True)

    class Meta:
        model = BatchRelease
        fields = [
            'id',
            'batch',
            'batch_number',
            'product_name',
            'decision',
            'decision_date',
            'decision_by',
            'decision_by_name',
            'manufacturing_record_reviewed',
            'qc_results_reviewed',
            'deviations_reviewed',
            'specifications_met',
            'has_deviations',
            'deviation_summary',
            'deviations_acceptable',
            'comments',
            'rejection_reason',
            'coa_generated',
            'coa_file',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'decision_by', 'decision_date',
        ]


class BatchReleaseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating batch release decisions."""

    class Meta:
        model = BatchRelease
        fields = [
            'batch',
            'decision',
            'manufacturing_record_reviewed',
            'qc_results_reviewed',
            'deviations_reviewed',
            'specifications_met',
            'has_deviations',
            'deviation_summary',
            'deviations_acceptable',
            'comments',
            'rejection_reason',
        ]

    def validate(self, attrs):
        """Validate release decision."""
        decision = attrs.get('decision')

        # For release, all checks must be completed
        if decision == BatchRelease.Decision.RELEASED:
            required_checks = [
                'manufacturing_record_reviewed',
                'qc_results_reviewed',
                'deviations_reviewed',
                'specifications_met',
            ]
            for check in required_checks:
                if not attrs.get(check):
                    raise serializers.ValidationError({
                        check: f'{check.replace("_", " ").title()} is required for release.'
                    })

            # If has deviations, must be acceptable
            if attrs.get('has_deviations') and not attrs.get('deviations_acceptable'):
                raise serializers.ValidationError({
                    'deviations_acceptable': 'Deviations must be marked acceptable for release.'
                })

        # For rejection, require reason
        if decision == BatchRelease.Decision.REJECTED:
            if not attrs.get('rejection_reason'):
                raise serializers.ValidationError({
                    'rejection_reason': 'Rejection reason required.'
                })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        validated_data['decision_by'] = user
        validated_data['decision_date'] = timezone.now()
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id

        return super().create(validated_data)
