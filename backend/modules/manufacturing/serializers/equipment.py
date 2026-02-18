"""
Equipment and calibration serializers.
"""
from rest_framework import serializers
from django.utils import timezone
from modules.manufacturing.models import (
    Equipment,
    CalibrationRecord,
    EquipmentUsage,
)


class EquipmentListSerializer(serializers.ModelSerializer):
    """Lightweight equipment serializer."""

    is_calibration_due = serializers.BooleanField(read_only=True)
    is_maintenance_due = serializers.BooleanField(read_only=True)
    is_qualified = serializers.BooleanField(read_only=True)

    class Meta:
        model = Equipment
        fields = [
            'id',
            'equipment_id',
            'name',
            'equipment_type',
            'location',
            'status',
            'is_calibration_due',
            'is_maintenance_due',
            'is_qualified',
            'next_calibration_date',
            'next_maintenance_date',
        ]


class EquipmentSerializer(serializers.ModelSerializer):
    """Full equipment serializer."""

    is_calibration_due = serializers.BooleanField(read_only=True)
    is_maintenance_due = serializers.BooleanField(read_only=True)
    is_qualified = serializers.BooleanField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    recent_calibrations = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = [
            'id',
            'equipment_id',
            'name',
            'description',
            'equipment_type',
            'manufacturer',
            'model_number',
            'serial_number',
            'location',
            'area',
            'room',
            'status',
            'installation_date',
            'commissioned_date',
            'warranty_expiry',
            'requires_calibration',
            'calibration_frequency_days',
            'last_calibration_date',
            'next_calibration_date',
            'is_calibration_due',
            'requires_preventive_maintenance',
            'maintenance_frequency_days',
            'last_maintenance_date',
            'next_maintenance_date',
            'is_maintenance_due',
            'iq_completed',
            'oq_completed',
            'pq_completed',
            'is_qualified',
            'operating_parameters',
            'associated_sops',
            'barcode',
            'notes',
            'recent_calibrations',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
            'last_calibration_date', 'next_calibration_date',
            'last_maintenance_date', 'next_maintenance_date',
        ]

    def get_recent_calibrations(self, obj):
        """Get last 3 calibration records."""
        records = obj.calibration_records.all()[:3]
        return [
            {
                'date': r.calibration_date,
                'result': r.result,
                'calibrated_by': r.calibrated_by.full_name if r.calibrated_by else None,
            }
            for r in records
        ]

    def validate_equipment_id(self, value):
        return value.upper()

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        return super().create(validated_data)


class CalibrationRecordSerializer(serializers.ModelSerializer):
    """Calibration record serializer."""

    equipment_id = serializers.CharField(source='equipment.equipment_id', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    calibrated_by_name = serializers.CharField(source='calibrated_by.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = CalibrationRecord
        fields = [
            'id',
            'equipment',
            'equipment_id',
            'equipment_name',
            'calibration_date',
            'calibrated_by',
            'calibrated_by_name',
            'calibration_type',
            'reference_standard',
            'reference_certificate',
            'result',
            'as_found_data',
            'as_left_data',
            'adjustment_made',
            'adjustment_details',
            'acceptance_criteria',
            'next_calibration_date',
            'certificate_number',
            'certificate_file',
            'reviewed_by',
            'reviewed_by_name',
            'reviewed_at',
            'notes',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'calibrated_by', 'reviewed_by', 'reviewed_at',
        ]


class CalibrationRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating calibration records."""

    class Meta:
        model = CalibrationRecord
        fields = [
            'equipment',
            'calibration_date',
            'calibration_type',
            'reference_standard',
            'reference_certificate',
            'result',
            'as_found_data',
            'as_left_data',
            'adjustment_made',
            'adjustment_details',
            'acceptance_criteria',
            'next_calibration_date',
            'certificate_number',
            'certificate_file',
            'notes',
        ]

    def validate(self, attrs):
        """Validate calibration record."""
        # Ensure next calibration date is in the future
        if attrs.get('next_calibration_date'):
            if attrs['next_calibration_date'] <= attrs['calibration_date']:
                raise serializers.ValidationError({
                    'next_calibration_date': 'Next calibration date must be after calibration date.'
                })

        # If result is fail, require notes
        if attrs.get('result') == CalibrationRecord.Result.FAIL:
            if not attrs.get('notes'):
                raise serializers.ValidationError({
                    'notes': 'Notes required for failed calibrations.'
                })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['calibrated_by'] = user
        validated_data['created_by'] = user
        return super().create(validated_data)


class EquipmentUsageSerializer(serializers.ModelSerializer):
    """Equipment usage serializer."""

    equipment_id_code = serializers.CharField(source='equipment.equipment_id', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    operated_by_name = serializers.CharField(source='operated_by.full_name', read_only=True)
    cleaning_completed_by_name = serializers.CharField(
        source='cleaning_completed_by.full_name',
        read_only=True,
        allow_null=True
    )
    duration = serializers.DurationField(read_only=True)

    class Meta:
        model = EquipmentUsage
        fields = [
            'id',
            'equipment',
            'equipment_id_code',
            'equipment_name',
            'batch',
            'batch_number',
            'batch_step',
            'start_time',
            'end_time',
            'duration',
            'operated_by',
            'operated_by_name',
            'pre_use_check_completed',
            'calibration_verified',
            'equipment_clean',
            'parameters_recorded',
            'equipment_barcode_scanned',
            'cleaning_required',
            'cleaning_completed',
            'cleaning_completed_by',
            'cleaning_completed_by_name',
            'cleaning_completed_at',
            'issues_encountered',
            'issue_details',
            'notes',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'operated_by',
            'cleaning_completed_by', 'cleaning_completed_at',
        ]


class EquipmentUsageCreateSerializer(serializers.ModelSerializer):
    """Serializer for recording equipment usage."""

    equipment_barcode = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = EquipmentUsage
        fields = [
            'equipment',
            'batch',
            'batch_step',
            'pre_use_check_completed',
            'equipment_clean',
            'parameters_recorded',
            'equipment_barcode',
            'notes',
        ]

    def validate(self, attrs):
        """Validate equipment usage."""
        equipment = attrs.get('equipment')

        # Check equipment is operational
        if equipment.status != Equipment.Status.OPERATIONAL:
            raise serializers.ValidationError({
                'equipment': f'Equipment is not operational. Status: {equipment.status}'
            })

        # Check calibration is current
        if equipment.requires_calibration and equipment.is_calibration_due:
            raise serializers.ValidationError({
                'equipment': 'Equipment calibration is due. Cannot use until calibrated.'
            })
            attrs['calibration_verified'] = False
        else:
            attrs['calibration_verified'] = True

        # Verify barcode if provided
        equipment_barcode = attrs.pop('equipment_barcode', None)
        if equipment_barcode:
            if equipment_barcode == equipment.barcode:
                attrs['equipment_barcode_scanned'] = True
            else:
                raise serializers.ValidationError({
                    'equipment_barcode': 'Barcode does not match equipment.'
                })

        # Check pre-use check
        if not attrs.get('pre_use_check_completed'):
            raise serializers.ValidationError({
                'pre_use_check_completed': 'Pre-use check must be completed.'
            })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['operated_by'] = user
        validated_data['start_time'] = timezone.now()
        validated_data['created_by'] = user
        return super().create(validated_data)


class EquipmentUsageCompleteSerializer(serializers.Serializer):
    """Serializer for completing equipment usage."""

    parameters_recorded = serializers.JSONField(required=False)
    issues_encountered = serializers.BooleanField(default=False)
    issue_details = serializers.CharField(required=False, allow_blank=True)
    cleaning_completed = serializers.BooleanField(default=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get('issues_encountered') and not attrs.get('issue_details'):
            raise serializers.ValidationError({
                'issue_details': 'Issue details required when issues are reported.'
            })
        return attrs
