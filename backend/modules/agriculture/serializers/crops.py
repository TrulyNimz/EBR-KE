"""
Crop management serializers.
"""
from rest_framework import serializers
from django.utils import timezone
from modules.agriculture.models import Crop, Field, CropBatch, FarmInput


class CropListSerializer(serializers.ModelSerializer):
    """Lightweight crop serializer."""

    batch_count = serializers.SerializerMethodField()

    class Meta:
        model = Crop
        fields = [
            'id',
            'code',
            'name',
            'variety',
            'crop_type',
            'days_to_maturity',
            'organic_certified',
            'is_active',
            'batch_count',
        ]

    def get_batch_count(self, obj):
        return obj.batches.count()


class CropSerializer(serializers.ModelSerializer):
    """Full crop serializer."""

    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = Crop
        fields = [
            'id',
            'code',
            'name',
            'scientific_name',
            'variety',
            'crop_type',
            'growing_season',
            'days_to_maturity',
            'optimal_temperature_min',
            'optimal_temperature_max',
            'water_requirements',
            'soil_requirements',
            'expected_yield_per_hectare',
            'yield_unit',
            'organic_certified',
            'fair_trade_eligible',
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


class FieldListSerializer(serializers.ModelSerializer):
    """Lightweight field serializer."""

    current_crop = serializers.SerializerMethodField()

    class Meta:
        model = Field
        fields = [
            'id',
            'field_code',
            'name',
            'area_hectares',
            'soil_type',
            'irrigation_type',
            'organic_certified',
            'is_active',
            'current_status',
            'current_crop',
        ]

    def get_current_crop(self, obj):
        current_batch = obj.crop_batches.filter(
            status__in=['planted', 'growing', 'ready']
        ).first()
        if current_batch:
            return current_batch.crop.name
        return None


class FieldSerializer(serializers.ModelSerializer):
    """Full field serializer."""

    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    recent_batches = serializers.SerializerMethodField()

    class Meta:
        model = Field
        fields = [
            'id',
            'field_code',
            'name',
            'location_description',
            'boundary_coordinates',
            'center_latitude',
            'center_longitude',
            'area_hectares',
            'arable_area_hectares',
            'soil_type',
            'soil_ph',
            'last_soil_test',
            'irrigation_type',
            'water_source',
            'organic_certified',
            'organic_certification_date',
            'organic_certificate_number',
            'is_active',
            'current_status',
            'notes',
            'recent_batches',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_recent_batches(self, obj):
        batches = obj.crop_batches.all()[:5]
        return [
            {
                'batch_number': b.batch_number,
                'crop': b.crop.name,
                'status': b.status,
                'planting_date': b.actual_planting_date,
            }
            for b in batches
        ]

    def validate_field_code(self, value):
        return value.upper()

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        return super().create(validated_data)


class CropBatchListSerializer(serializers.ModelSerializer):
    """Lightweight crop batch serializer."""

    crop_name = serializers.CharField(source='crop.name', read_only=True)
    field_name = serializers.CharField(source='field.name', read_only=True)

    class Meta:
        model = CropBatch
        fields = [
            'id',
            'batch_number',
            'crop_name',
            'field_name',
            'status',
            'planted_area_hectares',
            'actual_planting_date',
            'expected_harvest_date',
            'harvest_quantity',
            'harvest_unit',
        ]


class CropBatchSerializer(serializers.ModelSerializer):
    """Full crop batch serializer."""

    crop_name = serializers.CharField(source='crop.name', read_only=True)
    field_name = serializers.CharField(source='field.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    inputs = serializers.SerializerMethodField()

    class Meta:
        model = CropBatch
        fields = [
            'id',
            'batch_number',
            'crop',
            'crop_name',
            'field',
            'field_name',
            'ebr_batch',
            'status',
            'seed_lot_number',
            'seed_supplier',
            'seed_quantity_kg',
            'planned_planting_date',
            'actual_planting_date',
            'planting_method',
            'planted_area_hectares',
            'expected_harvest_date',
            'actual_harvest_start',
            'actual_harvest_end',
            'harvest_quantity',
            'harvest_unit',
            'yield_per_hectare',
            'quality_grade',
            'moisture_content',
            'storage_location',
            'storage_conditions',
            'weather_summary',
            'notes',
            'inputs',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'batch_number', 'created_at', 'updated_at', 'created_by',
        ]

    def get_inputs(self, obj):
        inputs = obj.inputs.all()[:10]
        return FarmInputSerializer(inputs, many=True).data


class CropBatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating crop batches."""

    class Meta:
        model = CropBatch
        fields = [
            'crop',
            'field',
            'seed_lot_number',
            'seed_supplier',
            'seed_quantity_kg',
            'planned_planting_date',
            'planting_method',
            'planted_area_hectares',
            'notes',
        ]

    def validate(self, attrs):
        field = attrs.get('field')

        # Check field is active
        if not field.is_active:
            raise serializers.ValidationError({
                'field': 'Field is not active.'
            })

        # Check field doesn't have an active crop
        active_batch = field.crop_batches.filter(
            status__in=['planted', 'growing', 'ready', 'harvesting']
        ).exists()
        if active_batch:
            raise serializers.ValidationError({
                'field': 'Field already has an active crop batch.'
            })

        return attrs

    def create(self, validated_data):
        import uuid
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        validated_data['batch_number'] = f"CB-{uuid.uuid4().hex[:10].upper()}"
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id

        return super().create(validated_data)


class FarmInputSerializer(serializers.ModelSerializer):
    """Farm input serializer."""

    crop_batch_number = serializers.CharField(source='crop_batch.batch_number', read_only=True)
    applied_by_name = serializers.CharField(source='applied_by.full_name', read_only=True)

    class Meta:
        model = FarmInput
        fields = [
            'id',
            'crop_batch',
            'crop_batch_number',
            'batch_step',
            'input_type',
            'product_name',
            'product_code',
            'active_ingredient',
            'application_date',
            'application_method',
            'quantity_applied',
            'quantity_unit',
            'application_rate',
            'area_treated_hectares',
            'applied_by',
            'applied_by_name',
            'pre_harvest_interval_days',
            're_entry_interval_hours',
            'weather_conditions',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'applied_by']


class FarmInputCreateSerializer(serializers.ModelSerializer):
    """Serializer for recording farm inputs."""

    class Meta:
        model = FarmInput
        fields = [
            'crop_batch',
            'batch_step',
            'input_type',
            'product_name',
            'product_code',
            'active_ingredient',
            'application_date',
            'application_method',
            'quantity_applied',
            'quantity_unit',
            'application_rate',
            'area_treated_hectares',
            'pre_harvest_interval_days',
            're_entry_interval_hours',
            'weather_conditions',
            'notes',
        ]

    def validate(self, attrs):
        crop_batch = attrs.get('crop_batch')

        # Check batch is in appropriate status
        if crop_batch.status not in ['planted', 'growing']:
            raise serializers.ValidationError({
                'crop_batch': f'Cannot add inputs to batch with status: {crop_batch.status}'
            })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['applied_by'] = user
        validated_data['created_by'] = user
        return super().create(validated_data)
