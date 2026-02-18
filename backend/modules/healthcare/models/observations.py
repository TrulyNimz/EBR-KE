"""
Healthcare Clinical Observation models.

Vital signs, assessments, and clinical notes.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditableModel


class VitalSigns(AuditableModel):
    """
    Patient vital signs recording.
    """

    patient = models.ForeignKey(
        'healthcare.Patient',
        on_delete=models.CASCADE,
        related_name='vital_signs'
    )

    # Recording information
    recorded_at = models.DateTimeField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='recorded_vitals'
    )

    # Temperature
    temperature = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Temperature in Celsius'
    )
    temperature_method = models.CharField(
        max_length=20,
        blank=True,
        help_text='e.g., oral, tympanic, axillary'
    )

    # Blood pressure
    systolic_bp = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Systolic blood pressure (mmHg)'
    )
    diastolic_bp = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Diastolic blood pressure (mmHg)'
    )
    bp_position = models.CharField(
        max_length=20,
        blank=True,
        help_text='e.g., sitting, standing, lying'
    )

    # Heart rate
    heart_rate = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Heart rate (beats per minute)'
    )
    heart_rhythm = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g., regular, irregular'
    )

    # Respiratory
    respiratory_rate = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Respiratory rate (breaths per minute)'
    )
    oxygen_saturation = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='SpO2 percentage'
    )
    oxygen_therapy = models.CharField(
        max_length=100,
        blank=True,
        help_text='e.g., room air, 2L nasal cannula'
    )

    # Pain assessment
    pain_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Pain score (0-10)'
    )
    pain_location = models.CharField(max_length=200, blank=True)

    # Consciousness
    consciousness_level = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g., alert, drowsy, unresponsive'
    )
    gcs_eye = models.PositiveIntegerField(null=True, blank=True)
    gcs_verbal = models.PositiveIntegerField(null=True, blank=True)
    gcs_motor = models.PositiveIntegerField(null=True, blank=True)

    # Weight and height
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Weight in kg'
    )
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Height in cm'
    )

    # Blood glucose
    blood_glucose = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Blood glucose (mmol/L)'
    )
    glucose_timing = models.CharField(
        max_length=20,
        blank=True,
        help_text='e.g., fasting, random, post-prandial'
    )

    # Notes
    notes = models.TextField(blank=True)

    # Linked batch step
    batch_step = models.ForeignKey(
        'batch_records.BatchStep',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vital_signs'
    )

    class Meta:
        db_table = 'healthcare_vital_signs'
        ordering = ['-recorded_at']
        verbose_name_plural = 'Vital signs'

    def __str__(self):
        return f'{self.patient.patient_number} - {self.recorded_at}'

    @property
    def gcs_total(self):
        """Calculate Glasgow Coma Scale total."""
        if all([self.gcs_eye, self.gcs_verbal, self.gcs_motor]):
            return self.gcs_eye + self.gcs_verbal + self.gcs_motor
        return None

    @property
    def bmi(self):
        """Calculate BMI if weight and height available."""
        if self.weight and self.height:
            height_m = self.height / 100
            return round(float(self.weight) / (height_m ** 2), 1)
        return None


class ClinicalNote(AuditableModel):
    """
    Clinical note/documentation.
    """

    class NoteType(models.TextChoices):
        ADMISSION = 'admission', 'Admission Note'
        PROGRESS = 'progress', 'Progress Note'
        CONSULTATION = 'consultation', 'Consultation Note'
        PROCEDURE = 'procedure', 'Procedure Note'
        DISCHARGE = 'discharge', 'Discharge Summary'
        NURSING = 'nursing', 'Nursing Note'
        OTHER = 'other', 'Other'

    patient = models.ForeignKey(
        'healthcare.Patient',
        on_delete=models.CASCADE,
        related_name='clinical_notes'
    )

    # Note metadata
    note_type = models.CharField(
        max_length=20,
        choices=NoteType.choices,
        default=NoteType.PROGRESS
    )
    title = models.CharField(max_length=255)

    # Author
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='clinical_notes'
    )
    authored_at = models.DateTimeField()

    # Content sections (SOAP format)
    subjective = models.TextField(
        blank=True,
        help_text='Patient symptoms, complaints, history'
    )
    objective = models.TextField(
        blank=True,
        help_text='Physical exam findings, vital signs, lab results'
    )
    assessment = models.TextField(
        blank=True,
        help_text='Diagnosis, clinical impression'
    )
    plan = models.TextField(
        blank=True,
        help_text='Treatment plan, orders, follow-up'
    )

    # Alternative: Free text content
    content = models.TextField(
        blank=True,
        help_text='Free text content if not using SOAP format'
    )

    # Diagnosis codes
    diagnosis_codes = models.JSONField(
        default=list,
        help_text='ICD-10 codes'
    )

    # Co-signature (if required)
    requires_cosignature = models.BooleanField(default=False)
    cosigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cosigned_notes'
    )
    cosigned_at = models.DateTimeField(null=True, blank=True)

    # Status
    is_final = models.BooleanField(
        default=False,
        help_text='Once finalized, note cannot be edited'
    )
    finalized_at = models.DateTimeField(null=True, blank=True)

    # Addendums
    parent_note = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='addendums'
    )
    is_addendum = models.BooleanField(default=False)

    class Meta:
        db_table = 'healthcare_clinical_notes'
        ordering = ['-authored_at']

    def __str__(self):
        return f'{self.patient.patient_number} - {self.title}'

    def save(self, *args, **kwargs):
        if self.pk and self.is_final:
            # Prevent editing finalized notes
            existing = ClinicalNote.objects.get(pk=self.pk)
            if existing.is_final:
                raise ValueError('Cannot modify a finalized note')
        super().save(*args, **kwargs)


class Assessment(AuditableModel):
    """
    Clinical assessment/screening tool.
    """

    class AssessmentType(models.TextChoices):
        FALL_RISK = 'fall_risk', 'Fall Risk Assessment'
        PRESSURE_ULCER = 'pressure_ulcer', 'Pressure Ulcer Risk'
        NUTRITION = 'nutrition', 'Nutritional Assessment'
        PAIN = 'pain', 'Pain Assessment'
        MENTAL_STATUS = 'mental_status', 'Mental Status Exam'
        FUNCTIONAL = 'functional', 'Functional Assessment'
        DISCHARGE = 'discharge', 'Discharge Readiness'
        CUSTOM = 'custom', 'Custom Assessment'

    patient = models.ForeignKey(
        'healthcare.Patient',
        on_delete=models.CASCADE,
        related_name='assessments'
    )

    # Assessment info
    assessment_type = models.CharField(
        max_length=30,
        choices=AssessmentType.choices
    )
    assessment_name = models.CharField(max_length=255)

    # Assessor
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='patient_assessments'
    )
    assessed_at = models.DateTimeField()

    # Assessment data (flexible JSON)
    responses = models.JSONField(
        default=dict,
        help_text='Assessment question responses'
    )

    # Scoring
    total_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    risk_level = models.CharField(max_length=50, blank=True)
    interpretation = models.TextField(blank=True)

    # Recommendations
    recommendations = models.JSONField(
        default=list,
        help_text='List of recommendations based on assessment'
    )
    interventions_required = models.JSONField(
        default=list,
        help_text='Required interventions'
    )

    # Linked batch step
    batch_step = models.ForeignKey(
        'batch_records.BatchStep',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assessments'
    )

    class Meta:
        db_table = 'healthcare_assessments'
        ordering = ['-assessed_at']

    def __str__(self):
        return f'{self.patient.patient_number} - {self.assessment_name}'
