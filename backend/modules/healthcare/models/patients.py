"""
Healthcare Patient models.

Patient records with encrypted PHI (Protected Health Information)
for HIPAA compliance and Kenya Data Protection Act 2019.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditableModel
from services.encryption.field_encryption import EncryptedFieldMixin


class Patient(EncryptedFieldMixin, AuditableModel):
    """
    Patient model with encrypted PHI fields.

    Sensitive fields are encrypted at rest using AES-256.
    """

    # Fields to encrypt
    encrypted_fields = [
        'national_id',
        'phone',
        'address',
        'emergency_contact_phone',
    ]

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        DISCHARGED = 'discharged', 'Discharged'
        TRANSFERRED = 'transferred', 'Transferred'
        DECEASED = 'deceased', 'Deceased'

    # Patient identifiers
    patient_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text='Unique patient identifier'
    )
    medical_record_number = models.CharField(
        max_length=50,
        blank=True,
        db_index=True
    )

    # Personal information (encrypted where sensitive)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)

    # Encrypted contact information
    national_id = models.TextField(blank=True, help_text='Encrypted')
    phone = models.TextField(blank=True, help_text='Encrypted')
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True, help_text='Encrypted')

    # Emergency contact (encrypted phone)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    emergency_contact_phone = models.TextField(blank=True, help_text='Encrypted')

    # Medical information
    blood_type = models.CharField(max_length=10, blank=True)
    allergies = models.JSONField(default=list, help_text='List of known allergies')
    chronic_conditions = models.JSONField(
        default=list,
        help_text='List of chronic conditions'
    )

    # Admission information
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    admission_date = models.DateTimeField(null=True, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    bed_number = models.CharField(max_length=20, blank=True)

    # Attending physician
    attending_physician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patients'
    )

    # Wristband/barcode
    wristband_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text='Barcode/RFID on patient wristband'
    )

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'healthcare_patients'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant_id', 'patient_number']),
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['last_name', 'first_name']),
        ]

    def __str__(self):
        return f'{self.patient_number} - {self.full_name}'

    @property
    def full_name(self):
        """Get patient's full name."""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(parts)

    @property
    def age(self):
        """Calculate patient age."""
        from datetime import date
        today = date.today()
        return (
            today.year - self.date_of_birth.year -
            ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    def _get_checksum_fields(self):
        """Fields for integrity checksum (excluding encrypted values)."""
        return {
            'patient_number': self.patient_number,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': str(self.date_of_birth),
            'status': self.status,
        }


class PatientAllergy(AuditableModel):
    """
    Patient allergy record.
    """

    class Severity(models.TextChoices):
        MILD = 'mild', 'Mild'
        MODERATE = 'moderate', 'Moderate'
        SEVERE = 'severe', 'Severe'
        LIFE_THREATENING = 'life_threatening', 'Life Threatening'

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='allergy_records'
    )

    allergen = models.CharField(max_length=200)
    allergen_type = models.CharField(
        max_length=50,
        help_text='e.g., medication, food, environmental'
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MODERATE
    )
    reaction = models.TextField(blank=True)
    onset_date = models.DateField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_allergies'
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'healthcare_patient_allergies'
        ordering = ['-severity', 'allergen']
        unique_together = ['patient', 'allergen']

    def __str__(self):
        return f'{self.patient.patient_number} - {self.allergen}'
