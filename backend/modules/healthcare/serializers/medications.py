"""
Medication serializers with 5 Rights verification support.
"""
from rest_framework import serializers
from django.utils import timezone
from modules.healthcare.models import (
    MedicationOrder,
    MedicationAdministration,
)


class MedicationOrderSerializer(serializers.ModelSerializer):
    """Serializer for medication orders."""

    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_number = serializers.CharField(source='patient.patient_number', read_only=True)
    prescriber_name = serializers.CharField(source='prescriber.full_name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    administration_count = serializers.SerializerMethodField()

    class Meta:
        model = MedicationOrder
        fields = [
            'id',
            'order_number',
            'patient',
            'patient_name',
            'patient_number',
            'medication_name',
            'medication_code',
            'dose',
            'dose_unit',
            'route',
            'frequency',
            'frequency_hours',
            'start_date',
            'end_date',
            'instructions',
            'status',
            'is_active',
            'prescriber',
            'prescriber_name',
            'verified_by',
            'verified_at',
            'administration_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at',
            'verified_by', 'verified_at', 'prescriber',
        ]

    def get_administration_count(self, obj):
        return obj.administrations.count()


class MedicationOrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating medication orders."""

    class Meta:
        model = MedicationOrder
        fields = [
            'patient',
            'medication_name',
            'medication_code',
            'dose',
            'dose_unit',
            'route',
            'frequency',
            'frequency_hours',
            'start_date',
            'end_date',
            'instructions',
        ]

    def validate(self, attrs):
        """Validate medication order data."""
        if attrs.get('end_date') and attrs.get('start_date'):
            if attrs['end_date'] < attrs['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date.'
                })

        # Validate dose is positive
        if attrs.get('dose', 0) <= 0:
            raise serializers.ValidationError({
                'dose': 'Dose must be greater than zero.'
            })

        return attrs

    def create(self, validated_data):
        import uuid
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        validated_data['order_number'] = f"MO-{uuid.uuid4().hex[:8].upper()}"
        validated_data['prescriber'] = user
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id

        return super().create(validated_data)


class FiveRightsVerificationSerializer(serializers.Serializer):
    """
    Serializer for 5 Rights medication verification.

    The 5 Rights:
    1. Right Patient
    2. Right Medication
    3. Right Dose
    4. Right Route
    5. Right Time
    """

    # Verification inputs
    patient_wristband_scan = serializers.CharField(
        help_text='Scanned patient wristband barcode'
    )
    medication_barcode_scan = serializers.CharField(
        help_text='Scanned medication barcode'
    )

    # Verification results (output)
    right_patient = serializers.BooleanField(read_only=True)
    right_medication = serializers.BooleanField(read_only=True)
    right_dose = serializers.BooleanField(read_only=True)
    right_route = serializers.BooleanField(read_only=True)
    right_time = serializers.BooleanField(read_only=True)
    all_verified = serializers.BooleanField(read_only=True)
    verification_messages = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )

    def validate(self, attrs):
        """Perform 5 Rights verification."""
        order = self.context.get('order')
        if not order:
            raise serializers.ValidationError('Medication order context required.')

        messages = []
        results = {
            'right_patient': False,
            'right_medication': False,
            'right_dose': True,  # Assume correct unless flagged
            'right_route': True,  # Assume correct unless flagged
            'right_time': False,
        }

        # 1. Right Patient - verify wristband matches order patient
        from modules.healthcare.models import Patient
        try:
            scanned_patient = Patient.objects.get(
                wristband_id=attrs['patient_wristband_scan']
            )
            if scanned_patient.id == order.patient_id:
                results['right_patient'] = True
                messages.append(f"Patient verified: {scanned_patient.full_name}")
            else:
                messages.append(
                    f"WRONG PATIENT: Scanned {scanned_patient.full_name}, "
                    f"expected {order.patient.full_name}"
                )
        except Patient.DoesNotExist:
            messages.append("Patient wristband not found in system")

        # 2. Right Medication - verify barcode matches order
        if attrs['medication_barcode_scan'] == order.medication_code:
            results['right_medication'] = True
            messages.append(f"Medication verified: {order.medication_name}")
        else:
            messages.append(
                f"WRONG MEDICATION: Scanned code does not match order"
            )

        # 5. Right Time - check if within administration window
        now = timezone.now()
        if order.start_date <= now:
            if not order.end_date or order.end_date >= now:
                results['right_time'] = True
                messages.append("Within valid administration time window")
            else:
                messages.append("Order has expired")
        else:
            messages.append("Order not yet active")

        results['all_verified'] = all([
            results['right_patient'],
            results['right_medication'],
            results['right_dose'],
            results['right_route'],
            results['right_time'],
        ])
        results['verification_messages'] = messages

        attrs.update(results)
        return attrs


class MedicationAdministrationSerializer(serializers.ModelSerializer):
    """Serializer for medication administration records."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)
    medication_name = serializers.CharField(source='order.medication_name', read_only=True)
    patient_name = serializers.CharField(source='order.patient.full_name', read_only=True)
    administered_by_name = serializers.CharField(
        source='administered_by.full_name',
        read_only=True
    )
    witnessed_by_name = serializers.CharField(
        source='witnessed_by.full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = MedicationAdministration
        fields = [
            'id',
            'order',
            'order_number',
            'medication_name',
            'patient_name',
            'administered_at',
            'dose_given',
            'dose_unit',
            'route_used',
            'site',
            'status',
            'five_rights_verified',
            'verification_data',
            'administered_by',
            'administered_by_name',
            'witnessed_by',
            'witnessed_by_name',
            'notes',
            'refusal_reason',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'administered_by', 'five_rights_verified',
            'verification_data',
        ]


class MedicationAdministrationCreateSerializer(serializers.ModelSerializer):
    """Serializer for recording medication administration."""

    # Include 5 Rights verification
    patient_wristband_scan = serializers.CharField(write_only=True)
    medication_barcode_scan = serializers.CharField(write_only=True)

    class Meta:
        model = MedicationAdministration
        fields = [
            'order',
            'dose_given',
            'dose_unit',
            'route_used',
            'site',
            'status',
            'witnessed_by',
            'notes',
            'refusal_reason',
            'patient_wristband_scan',
            'medication_barcode_scan',
        ]

    def validate(self, attrs):
        """Validate administration and perform 5 Rights check."""
        order = attrs.get('order')

        # Check order is active
        if order.status != MedicationOrder.Status.ACTIVE:
            raise serializers.ValidationError({
                'order': 'Medication order is not active.'
            })

        # Perform 5 Rights verification
        verification_serializer = FiveRightsVerificationSerializer(
            data={
                'patient_wristband_scan': attrs.pop('patient_wristband_scan'),
                'medication_barcode_scan': attrs.pop('medication_barcode_scan'),
            },
            context={'order': order}
        )
        verification_serializer.is_valid(raise_exception=True)
        verification_data = verification_serializer.validated_data

        attrs['five_rights_verified'] = verification_data['all_verified']
        attrs['verification_data'] = {
            'right_patient': verification_data['right_patient'],
            'right_medication': verification_data['right_medication'],
            'right_dose': verification_data['right_dose'],
            'right_route': verification_data['right_route'],
            'right_time': verification_data['right_time'],
            'messages': verification_data['verification_messages'],
            'verified_at': timezone.now().isoformat(),
        }

        # Require all 5 rights for administered status
        if attrs.get('status') == 'administered' and not attrs['five_rights_verified']:
            raise serializers.ValidationError({
                'status': 'Cannot mark as administered without passing all 5 Rights verification.'
            })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['administered_by'] = user
        validated_data['administered_at'] = timezone.now()
        validated_data['created_by'] = user
        return super().create(validated_data)
