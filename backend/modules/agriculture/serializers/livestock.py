"""
Livestock management serializers.
"""
from rest_framework import serializers
from django.utils import timezone
from modules.agriculture.models import (
    AnimalSpecies,
    Animal,
    AnimalHealthRecord,
    AnimalProductionRecord,
)


class AnimalSpeciesSerializer(serializers.ModelSerializer):
    """Animal species serializer."""

    animal_count = serializers.SerializerMethodField()

    class Meta:
        model = AnimalSpecies
        fields = [
            'id',
            'code',
            'name',
            'scientific_name',
            'production_types',
            'gestation_days',
            'maturity_age_months',
            'is_active',
            'animal_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_animal_count(self, obj):
        return obj.animals.filter(status='active').count()

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        return super().create(validated_data)


class AnimalListSerializer(serializers.ModelSerializer):
    """Lightweight animal serializer."""

    species_name = serializers.CharField(source='species.name', read_only=True)
    age_months = serializers.IntegerField(read_only=True)

    class Meta:
        model = Animal
        fields = [
            'id',
            'tag_number',
            'electronic_id',
            'name',
            'species_name',
            'breed',
            'sex',
            'birth_date',
            'age_months',
            'status',
            'current_location',
            'production_group',
        ]


class AnimalSerializer(serializers.ModelSerializer):
    """Full animal serializer."""

    species_name = serializers.CharField(source='species.name', read_only=True)
    dam_tag = serializers.CharField(source='dam.tag_number', read_only=True, allow_null=True)
    sire_tag = serializers.CharField(source='sire.tag_number', read_only=True, allow_null=True)
    age_months = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    recent_health_records = serializers.SerializerMethodField()
    recent_production = serializers.SerializerMethodField()

    class Meta:
        model = Animal
        fields = [
            'id',
            'tag_number',
            'electronic_id',
            'name',
            'species',
            'species_name',
            'breed',
            'sex',
            'birth_date',
            'birth_weight_kg',
            'age_months',
            'dam',
            'dam_tag',
            'sire',
            'sire_tag',
            'acquisition_date',
            'acquisition_type',
            'acquisition_source',
            'acquisition_price',
            'status',
            'status_date',
            'status_notes',
            'current_location',
            'pen_number',
            'current_weight_kg',
            'last_weight_date',
            'color_markings',
            'production_group',
            'notes',
            'recent_health_records',
            'recent_production',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_recent_health_records(self, obj):
        records = obj.health_records.all()[:5]
        return [
            {
                'record_type': r.record_type,
                'record_date': r.record_date,
                'product_name': r.product_name,
            }
            for r in records
        ]

    def get_recent_production(self, obj):
        records = obj.production_records.all()[:5]
        return [
            {
                'production_type': r.production_type,
                'production_date': r.production_date,
                'quantity': r.quantity,
                'unit': r.unit,
            }
            for r in records
        ]


class AnimalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating animals."""

    class Meta:
        model = Animal
        fields = [
            'tag_number',
            'electronic_id',
            'name',
            'species',
            'breed',
            'sex',
            'birth_date',
            'birth_weight_kg',
            'dam',
            'sire',
            'acquisition_date',
            'acquisition_type',
            'acquisition_source',
            'acquisition_price',
            'current_location',
            'pen_number',
            'color_markings',
            'production_group',
            'notes',
        ]

    def validate_tag_number(self, value):
        return value.upper()

    def validate(self, attrs):
        # Validate parentage sex
        if attrs.get('dam') and attrs['dam'].sex != Animal.Sex.FEMALE:
            raise serializers.ValidationError({
                'dam': 'Dam must be female.'
            })
        if attrs.get('sire') and attrs['sire'].sex != Animal.Sex.MALE:
            raise serializers.ValidationError({
                'sire': 'Sire must be male.'
            })
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        return super().create(validated_data)


class AnimalHealthRecordSerializer(serializers.ModelSerializer):
    """Animal health record serializer."""

    animal_tag = serializers.CharField(source='animal.tag_number', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.full_name', read_only=True)

    class Meta:
        model = AnimalHealthRecord
        fields = [
            'id',
            'animal',
            'animal_tag',
            'batch_step',
            'record_type',
            'record_date',
            'product_name',
            'product_batch',
            'dosage',
            'route',
            'withdrawal_period_days',
            'diagnosis',
            'symptoms',
            'body_condition_score',
            'temperature',
            'performed_by',
            'performed_by_name',
            'veterinarian',
            'cost',
            'follow_up_required',
            'follow_up_date',
            'follow_up_notes',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'performed_by']


class AnimalHealthRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating health records."""

    class Meta:
        model = AnimalHealthRecord
        fields = [
            'animal',
            'batch_step',
            'record_type',
            'record_date',
            'product_name',
            'product_batch',
            'dosage',
            'route',
            'withdrawal_period_days',
            'diagnosis',
            'symptoms',
            'body_condition_score',
            'temperature',
            'veterinarian',
            'cost',
            'follow_up_required',
            'follow_up_date',
            'follow_up_notes',
            'notes',
        ]

    def validate(self, attrs):
        if attrs.get('follow_up_required') and not attrs.get('follow_up_date'):
            raise serializers.ValidationError({
                'follow_up_date': 'Follow-up date required when follow-up is marked required.'
            })
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['performed_by'] = user
        validated_data['created_by'] = user
        return super().create(validated_data)


class AnimalProductionRecordSerializer(serializers.ModelSerializer):
    """Animal production record serializer."""

    animal_tag = serializers.CharField(source='animal.tag_number', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True)

    class Meta:
        model = AnimalProductionRecord
        fields = [
            'id',
            'animal',
            'animal_tag',
            'batch_step',
            'production_type',
            'production_date',
            'quantity',
            'unit',
            'quality_grade',
            'quality_notes',
            'fat_percentage',
            'protein_percentage',
            'somatic_cell_count',
            'recorded_by',
            'recorded_by_name',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'recorded_by']


class AnimalProductionRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating production records."""

    class Meta:
        model = AnimalProductionRecord
        fields = [
            'animal',
            'batch_step',
            'production_type',
            'production_date',
            'quantity',
            'unit',
            'quality_grade',
            'quality_notes',
            'fat_percentage',
            'protein_percentage',
            'somatic_cell_count',
            'notes',
        ]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Quantity must be greater than zero.')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['recorded_by'] = user
        validated_data['created_by'] = user
        return super().create(validated_data)
