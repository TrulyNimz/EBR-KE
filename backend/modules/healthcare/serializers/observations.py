"""
Clinical observation serializers.
"""
from rest_framework import serializers
from django.utils import timezone
from modules.healthcare.models import VitalSigns, ClinicalNote, Assessment


class VitalSignsSerializer(serializers.ModelSerializer):
    """Serializer for vital signs."""

    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_number = serializers.CharField(source='patient.patient_number', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True)
    is_abnormal = serializers.SerializerMethodField()

    class Meta:
        model = VitalSigns
        fields = [
            'id',
            'patient',
            'patient_name',
            'patient_number',
            'recorded_at',
            'temperature',
            'temperature_unit',
            'pulse',
            'respiratory_rate',
            'blood_pressure_systolic',
            'blood_pressure_diastolic',
            'oxygen_saturation',
            'pain_level',
            'weight',
            'weight_unit',
            'height',
            'height_unit',
            'notes',
            'is_abnormal',
            'recorded_by',
            'recorded_by_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'recorded_by', 'recorded_at']

    def get_is_abnormal(self, obj):
        """Check if any vital signs are outside normal ranges."""
        abnormal = []

        # Temperature (normal: 36.1-37.2 C)
        if obj.temperature:
            if obj.temperature < 36.1 or obj.temperature > 37.2:
                abnormal.append('temperature')

        # Pulse (normal adult: 60-100 bpm)
        if obj.pulse:
            if obj.pulse < 60 or obj.pulse > 100:
                abnormal.append('pulse')

        # Respiratory rate (normal adult: 12-20)
        if obj.respiratory_rate:
            if obj.respiratory_rate < 12 or obj.respiratory_rate > 20:
                abnormal.append('respiratory_rate')

        # Blood pressure (normal: <120/<80)
        if obj.blood_pressure_systolic:
            if obj.blood_pressure_systolic >= 140 or obj.blood_pressure_systolic < 90:
                abnormal.append('blood_pressure_systolic')
        if obj.blood_pressure_diastolic:
            if obj.blood_pressure_diastolic >= 90 or obj.blood_pressure_diastolic < 60:
                abnormal.append('blood_pressure_diastolic')

        # Oxygen saturation (normal: >95%)
        if obj.oxygen_saturation:
            if obj.oxygen_saturation < 95:
                abnormal.append('oxygen_saturation')

        return abnormal if abnormal else None


class VitalSignsCreateSerializer(serializers.ModelSerializer):
    """Serializer for recording vital signs."""

    class Meta:
        model = VitalSigns
        fields = [
            'patient',
            'temperature',
            'temperature_unit',
            'pulse',
            'respiratory_rate',
            'blood_pressure_systolic',
            'blood_pressure_diastolic',
            'oxygen_saturation',
            'pain_level',
            'weight',
            'weight_unit',
            'height',
            'height_unit',
            'notes',
        ]

    def validate_temperature(self, value):
        """Validate temperature is within plausible range."""
        if value and (value < 30 or value > 45):
            raise serializers.ValidationError(
                'Temperature must be between 30 and 45 degrees.'
            )
        return value

    def validate_pulse(self, value):
        """Validate pulse is within plausible range."""
        if value and (value < 20 or value > 300):
            raise serializers.ValidationError(
                'Pulse must be between 20 and 300 bpm.'
            )
        return value

    def validate_oxygen_saturation(self, value):
        """Validate O2 sat is percentage."""
        if value and (value < 0 or value > 100):
            raise serializers.ValidationError(
                'Oxygen saturation must be between 0 and 100%.'
            )
        return value

    def validate_pain_level(self, value):
        """Validate pain level is 0-10."""
        if value is not None and (value < 0 or value > 10):
            raise serializers.ValidationError(
                'Pain level must be between 0 and 10.'
            )
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        validated_data['recorded_by'] = user
        validated_data['recorded_at'] = timezone.now()
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id

        return super().create(validated_data)


class ClinicalNoteSerializer(serializers.ModelSerializer):
    """Serializer for clinical notes."""

    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_number = serializers.CharField(source='patient.patient_number', read_only=True)
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    cosigned_by_name = serializers.CharField(
        source='cosigned_by.full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = ClinicalNote
        fields = [
            'id',
            'patient',
            'patient_name',
            'patient_number',
            'note_type',
            'title',
            'content',
            'is_confidential',
            'status',
            'author',
            'author_name',
            'authored_at',
            'cosigned_by',
            'cosigned_by_name',
            'cosigned_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'author', 'authored_at',
            'cosigned_by', 'cosigned_at',
        ]


class ClinicalNoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating clinical notes."""

    class Meta:
        model = ClinicalNote
        fields = [
            'patient',
            'note_type',
            'title',
            'content',
            'is_confidential',
        ]

    def validate_content(self, value):
        """Ensure note content is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError('Note content cannot be empty.')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        validated_data['author'] = user
        validated_data['authored_at'] = timezone.now()
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        validated_data['status'] = ClinicalNote.Status.DRAFT

        return super().create(validated_data)


class ClinicalNoteSignSerializer(serializers.Serializer):
    """Serializer for signing/co-signing clinical notes."""

    action = serializers.ChoiceField(choices=['sign', 'cosign'])
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        """Verify user password for signature."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Invalid password.')
        return value


class AssessmentSerializer(serializers.ModelSerializer):
    """Serializer for patient assessments."""

    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_number = serializers.CharField(source='patient.patient_number', read_only=True)
    assessed_by_name = serializers.CharField(source='assessed_by.full_name', read_only=True)

    class Meta:
        model = Assessment
        fields = [
            'id',
            'patient',
            'patient_name',
            'patient_number',
            'assessment_type',
            'assessment_date',
            'chief_complaint',
            'history_of_present_illness',
            'physical_exam_findings',
            'assessment_summary',
            'plan',
            'diagnosis_codes',
            'risk_level',
            'follow_up_required',
            'follow_up_date',
            'assessed_by',
            'assessed_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'assessed_by']


class AssessmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating assessments."""

    class Meta:
        model = Assessment
        fields = [
            'patient',
            'assessment_type',
            'chief_complaint',
            'history_of_present_illness',
            'physical_exam_findings',
            'assessment_summary',
            'plan',
            'diagnosis_codes',
            'risk_level',
            'follow_up_required',
            'follow_up_date',
        ]

    def validate(self, attrs):
        """Validate assessment data."""
        if attrs.get('follow_up_required') and not attrs.get('follow_up_date'):
            raise serializers.ValidationError({
                'follow_up_date': 'Follow-up date required when follow-up is marked as required.'
            })
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        validated_data['assessed_by'] = user
        validated_data['assessment_date'] = timezone.now()
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id

        return super().create(validated_data)
