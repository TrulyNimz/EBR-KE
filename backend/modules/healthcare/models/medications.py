"""
Healthcare Medication models.

Medication tracking with 5 Rights verification:
- Right Patient
- Right Medication
- Right Dose
- Right Route
- Right Time
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from apps.core.models import AuditableModel


class Medication(AuditableModel):
    """
    Medication catalog entry.
    """

    class DrugClass(models.TextChoices):
        ANALGESIC = 'analgesic', 'Analgesic'
        ANTIBIOTIC = 'antibiotic', 'Antibiotic'
        ANTIVIRAL = 'antiviral', 'Antiviral'
        CARDIOVASCULAR = 'cardiovascular', 'Cardiovascular'
        DIABETES = 'diabetes', 'Diabetes'
        PSYCHIATRIC = 'psychiatric', 'Psychiatric'
        RESPIRATORY = 'respiratory', 'Respiratory'
        OTHER = 'other', 'Other'

    # Identification
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255)
    brand_names = models.JSONField(default=list)

    # Classification
    drug_class = models.CharField(
        max_length=50,
        choices=DrugClass.choices,
        default=DrugClass.OTHER
    )
    controlled_substance = models.BooleanField(default=False)
    controlled_schedule = models.CharField(
        max_length=10,
        blank=True,
        help_text='e.g., Schedule II, III'
    )

    # Dosage information
    strength = models.CharField(max_length=100)
    strength_unit = models.CharField(max_length=20)
    dosage_form = models.CharField(
        max_length=50,
        help_text='e.g., tablet, capsule, injection'
    )
    route = models.CharField(
        max_length=50,
        help_text='e.g., oral, IV, IM, topical'
    )

    # Clinical information
    indications = models.TextField(blank=True)
    contraindications = models.TextField(blank=True)
    side_effects = models.TextField(blank=True)
    interactions = models.JSONField(
        default=list,
        help_text='List of drug interaction warnings'
    )
    max_daily_dose = models.CharField(max_length=100, blank=True)

    # High-alert medication flag
    high_alert = models.BooleanField(
        default=False,
        help_text='Requires additional verification'
    )

    # Barcode
    barcode = models.CharField(max_length=100, blank=True, db_index=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'healthcare_medications'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} {self.strength}{self.strength_unit}'


class MedicationOrder(AuditableModel):
    """
    Medication order (prescription) for a patient.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Verification'
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        DISCONTINUED = 'discontinued', 'Discontinued'
        HELD = 'held', 'On Hold'

    class Frequency(models.TextChoices):
        ONCE = 'once', 'Once'
        BID = 'bid', 'Twice Daily (BID)'
        TID = 'tid', 'Three Times Daily (TID)'
        QID = 'qid', 'Four Times Daily (QID)'
        Q4H = 'q4h', 'Every 4 Hours'
        Q6H = 'q6h', 'Every 6 Hours'
        Q8H = 'q8h', 'Every 8 Hours'
        Q12H = 'q12h', 'Every 12 Hours'
        DAILY = 'daily', 'Daily'
        PRN = 'prn', 'As Needed (PRN)'
        STAT = 'stat', 'Immediately (STAT)'

    # Patient
    patient = models.ForeignKey(
        'healthcare.Patient',
        on_delete=models.PROTECT,
        related_name='medication_orders'
    )

    # Medication
    medication = models.ForeignKey(
        Medication,
        on_delete=models.PROTECT,
        related_name='orders'
    )

    # Order details
    order_number = models.CharField(max_length=50, unique=True)
    dose = models.DecimalField(max_digits=10, decimal_places=4)
    dose_unit = models.CharField(max_length=20)
    route = models.CharField(max_length=50)
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.DAILY
    )
    frequency_custom = models.CharField(
        max_length=200,
        blank=True,
        help_text='Custom frequency instructions'
    )

    # Timing
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    scheduled_times = models.JSONField(
        default=list,
        help_text='List of scheduled administration times'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Ordering provider
    ordering_provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='medication_orders'
    )

    # Pharmacy verification
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_medication_orders'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Instructions
    instructions = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)

    # Linked batch record
    batch = models.ForeignKey(
        'batch_records.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medication_orders'
    )

    # Digital signatures
    signatures = GenericRelation(
        'audit.DigitalSignature',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'healthcare_medication_orders'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order_number} - {self.patient.patient_number}'


class MedicationAdministration(AuditableModel):
    """
    Record of medication administration.

    Implements 5 Rights verification with digital signature.
    """

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        ADMINISTERED = 'administered', 'Administered'
        MISSED = 'missed', 'Missed'
        HELD = 'held', 'Held'
        REFUSED = 'refused', 'Refused by Patient'
        NOT_GIVEN = 'not_given', 'Not Given'

    # Order reference
    order = models.ForeignKey(
        MedicationOrder,
        on_delete=models.PROTECT,
        related_name='administrations'
    )

    # Scheduling
    scheduled_time = models.DateTimeField()
    actual_time = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    status_reason = models.TextField(blank=True)

    # Actual administration details
    actual_dose = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )
    actual_route = models.CharField(max_length=50, blank=True)

    # 5 Rights Verification
    right_patient_verified = models.BooleanField(default=False)
    right_medication_verified = models.BooleanField(default=False)
    right_dose_verified = models.BooleanField(default=False)
    right_route_verified = models.BooleanField(default=False)
    right_time_verified = models.BooleanField(default=False)
    all_rights_verified = models.BooleanField(default=False)

    # Verification methods
    patient_wristband_scanned = models.BooleanField(default=False)
    medication_barcode_scanned = models.BooleanField(default=False)

    # Administered by
    administered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='medication_administrations'
    )

    # Witness (for controlled substances)
    witness = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='witnessed_administrations'
    )

    # Patient response
    patient_response = models.TextField(blank=True)
    adverse_reaction = models.BooleanField(default=False)
    adverse_reaction_details = models.TextField(blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # Digital signatures
    signatures = GenericRelation(
        'audit.DigitalSignature',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    class Meta:
        db_table = 'healthcare_medication_administrations'
        ordering = ['-scheduled_time']

    def __str__(self):
        return f'{self.order.order_number} - {self.scheduled_time}'

    def save(self, *args, **kwargs):
        # Update all_rights_verified flag
        self.all_rights_verified = (
            self.right_patient_verified and
            self.right_medication_verified and
            self.right_dose_verified and
            self.right_route_verified and
            self.right_time_verified
        )
        super().save(*args, **kwargs)

    def verify_five_rights(
        self,
        patient_scan: str,
        medication_scan: str,
        administered_by
    ):
        """
        Verify the 5 Rights for medication administration.

        Args:
            patient_scan: Scanned patient wristband ID
            medication_scan: Scanned medication barcode
            administered_by: User administering the medication
        """
        from django.utils import timezone

        # Right Patient: Verify wristband matches patient
        if patient_scan == self.order.patient.wristband_id:
            self.right_patient_verified = True
            self.patient_wristband_scanned = True

        # Right Medication: Verify barcode matches medication
        if medication_scan == self.order.medication.barcode:
            self.right_medication_verified = True
            self.medication_barcode_scanned = True

        # Right Dose: Marked as verified if using ordered dose
        self.right_dose_verified = True
        self.actual_dose = self.order.dose

        # Right Route: Marked as verified if using ordered route
        self.right_route_verified = True
        self.actual_route = self.order.route

        # Right Time: Check if within acceptable window (±30 min)
        now = timezone.now()
        time_diff = abs((now - self.scheduled_time).total_seconds())
        if time_diff <= 1800:  # 30 minutes in seconds
            self.right_time_verified = True

        self.administered_by = administered_by
        self.actual_time = now
        self.save()

        return self.all_rights_verified
