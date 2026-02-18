"""
Patient serializers with PHI handling.
"""
from rest_framework import serializers
from django.utils import timezone
from modules.healthcare.models import Patient, PatientAllergy


class PatientAllergySerializer(serializers.ModelSerializer):
    """Serializer for patient allergies."""

    verified_by_name = serializers.CharField(
        source='verified_by.full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = PatientAllergy
        fields = [
            'id',
            'allergen',
            'allergen_type',
            'severity',
            'reaction',
            'onset_date',
            'verified',
            'verified_by',
            'verified_by_name',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'verified_by']


class PatientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for patient lists (minimal PHI exposure)."""

    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    allergy_count = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_number',
            'medical_record_number',
            'full_name',
            'date_of_birth',
            'age',
            'gender',
            'status',
            'ward',
            'bed_number',
            'allergy_count',
            'created_at',
        ]

    def get_allergy_count(self, obj):
        return obj.allergy_records.count()


class PatientSerializer(serializers.ModelSerializer):
    """Full patient serializer with decrypted PHI."""

    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    allergy_records = PatientAllergySerializer(many=True, read_only=True)
    attending_physician_name = serializers.CharField(
        source='attending_physician.full_name',
        read_only=True,
        allow_null=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True
    )

    # Decrypted fields (handled by model's EncryptedFieldMixin)
    phone_decrypted = serializers.SerializerMethodField()
    national_id_decrypted = serializers.SerializerMethodField()
    address_decrypted = serializers.SerializerMethodField()
    emergency_contact_phone_decrypted = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_number',
            'medical_record_number',
            'first_name',
            'middle_name',
            'last_name',
            'full_name',
            'date_of_birth',
            'age',
            'gender',
            'national_id_decrypted',
            'phone_decrypted',
            'email',
            'address_decrypted',
            'emergency_contact_name',
            'emergency_contact_relationship',
            'emergency_contact_phone_decrypted',
            'blood_type',
            'allergies',
            'chronic_conditions',
            'status',
            'admission_date',
            'discharge_date',
            'ward',
            'bed_number',
            'attending_physician',
            'attending_physician_name',
            'wristband_id',
            'allergy_records',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
            'patient_number',  # Auto-generated
        ]

    def get_phone_decrypted(self, obj):
        return obj.decrypt_field('phone') if obj.phone else None

    def get_national_id_decrypted(self, obj):
        return obj.decrypt_field('national_id') if obj.national_id else None

    def get_address_decrypted(self, obj):
        return obj.decrypt_field('address') if obj.address else None

    def get_emergency_contact_phone_decrypted(self, obj):
        return obj.decrypt_field('emergency_contact_phone') if obj.emergency_contact_phone else None


class PatientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating patients with encryption."""

    # Accept plain text, will be encrypted on save
    phone = serializers.CharField(required=False, allow_blank=True)
    national_id = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Patient
        fields = [
            'first_name',
            'middle_name',
            'last_name',
            'date_of_birth',
            'gender',
            'national_id',
            'phone',
            'email',
            'address',
            'emergency_contact_name',
            'emergency_contact_relationship',
            'emergency_contact_phone',
            'blood_type',
            'allergies',
            'chronic_conditions',
            'ward',
            'bed_number',
            'attending_physician',
        ]

    def validate_date_of_birth(self, value):
        """Ensure date of birth is not in the future."""
        if value > timezone.now().date():
            raise serializers.ValidationError('Date of birth cannot be in the future.')
        return value

    def validate_email(self, value):
        """Validate email format if provided."""
        if value and '@' not in value:
            raise serializers.ValidationError('Invalid email format.')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        # Generate patient number
        import uuid
        validated_data['patient_number'] = f"PT-{uuid.uuid4().hex[:8].upper()}"
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id

        patient = Patient(**validated_data)
        # Encrypt sensitive fields before saving
        patient.encrypt_fields()
        patient.save()
        return patient

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.encrypt_fields()
        instance.save()
        return instance


class PatientAdmissionSerializer(serializers.Serializer):
    """Serializer for patient admission."""

    ward = serializers.CharField(max_length=100)
    bed_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    attending_physician = serializers.PrimaryKeyRelatedField(
        queryset=None,  # Set in __init__
        required=False,
        allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['attending_physician'].queryset = User.objects.filter(is_active=True)


class PatientDischargeSerializer(serializers.Serializer):
    """Serializer for patient discharge."""

    discharge_notes = serializers.CharField(required=False, allow_blank=True)
    follow_up_instructions = serializers.CharField(required=False, allow_blank=True)
    discharge_diagnosis = serializers.CharField(required=False, allow_blank=True)
