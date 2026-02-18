"""
Manufacturing Equipment models.

Tracks equipment, calibration, and maintenance for
GMP compliance.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditableModel


class Equipment(AuditableModel):
    """
    Manufacturing equipment/instrument.
    """

    class Status(models.TextChoices):
        OPERATIONAL = 'operational', 'Operational'
        CALIBRATION_DUE = 'calibration_due', 'Calibration Due'
        UNDER_MAINTENANCE = 'maintenance', 'Under Maintenance'
        OUT_OF_SERVICE = 'out_of_service', 'Out of Service'
        RETIRED = 'retired', 'Retired'

    class EquipmentType(models.TextChoices):
        WEIGHING = 'weighing', 'Weighing Scale/Balance'
        MIXING = 'mixing', 'Mixer/Blender'
        GRANULATION = 'granulation', 'Granulator'
        COMPRESSION = 'compression', 'Tablet Press'
        COATING = 'coating', 'Coating Machine'
        PACKAGING = 'packaging', 'Packaging Equipment'
        LABORATORY = 'laboratory', 'Laboratory Instrument'
        ENVIRONMENTAL = 'environmental', 'Environmental Monitor'
        OTHER = 'other', 'Other'

    # Identification
    equipment_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    equipment_type = models.CharField(
        max_length=20,
        choices=EquipmentType.choices,
        default=EquipmentType.OTHER
    )

    # Manufacturer info
    manufacturer = models.CharField(max_length=200, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)

    # Location
    location = models.CharField(max_length=200)
    area = models.CharField(max_length=100, blank=True)
    room = models.CharField(max_length=100, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPERATIONAL
    )

    # Installation and commissioning
    installation_date = models.DateField(null=True, blank=True)
    commissioned_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)

    # Calibration settings
    requires_calibration = models.BooleanField(default=True)
    calibration_frequency_days = models.PositiveIntegerField(
        default=365,
        help_text='Calibration frequency in days'
    )
    last_calibration_date = models.DateField(null=True, blank=True)
    next_calibration_date = models.DateField(null=True, blank=True)

    # Maintenance settings
    requires_preventive_maintenance = models.BooleanField(default=True)
    maintenance_frequency_days = models.PositiveIntegerField(
        default=90,
        help_text='Maintenance frequency in days'
    )
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)

    # Qualification status
    iq_completed = models.BooleanField(
        default=False,
        help_text='Installation Qualification completed'
    )
    oq_completed = models.BooleanField(
        default=False,
        help_text='Operational Qualification completed'
    )
    pq_completed = models.BooleanField(
        default=False,
        help_text='Performance Qualification completed'
    )

    # Operating parameters
    operating_parameters = models.JSONField(
        default=dict,
        help_text='Equipment operating parameters and limits'
    )

    # SOPs
    associated_sops = models.JSONField(
        default=list,
        help_text='List of associated SOP numbers'
    )

    # Barcode
    barcode = models.CharField(max_length=100, blank=True, db_index=True)

    # Notes
    notes = models.TextField(blank=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'manufacturing_equipment'
        ordering = ['equipment_id']
        verbose_name_plural = 'Equipment'

    def __str__(self):
        return f'{self.equipment_id} - {self.name}'

    @property
    def is_calibration_due(self):
        """Check if calibration is due."""
        from datetime import date
        if self.next_calibration_date:
            return date.today() >= self.next_calibration_date
        return False

    @property
    def is_maintenance_due(self):
        """Check if maintenance is due."""
        from datetime import date
        if self.next_maintenance_date:
            return date.today() >= self.next_maintenance_date
        return False

    @property
    def is_qualified(self):
        """Check if equipment is fully qualified."""
        return self.iq_completed and self.oq_completed and self.pq_completed


class CalibrationRecord(AuditableModel):
    """
    Equipment calibration record.
    """

    class Result(models.TextChoices):
        PASS = 'pass', 'Pass'
        FAIL = 'fail', 'Fail'
        PASS_WITH_ADJUSTMENT = 'pass_adjusted', 'Pass with Adjustment'

    # Equipment reference
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='calibration_records'
    )

    # Calibration details
    calibration_date = models.DateField()
    calibrated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='calibrations_performed'
    )
    calibration_type = models.CharField(
        max_length=50,
        help_text='e.g., Annual, Quarterly, As Found'
    )

    # Reference standards
    reference_standard = models.CharField(max_length=255, blank=True)
    reference_certificate = models.CharField(max_length=100, blank=True)

    # Results
    result = models.CharField(
        max_length=20,
        choices=Result.choices
    )
    as_found_data = models.JSONField(
        default=dict,
        help_text='Measurements before adjustment'
    )
    as_left_data = models.JSONField(
        default=dict,
        help_text='Measurements after adjustment'
    )
    adjustment_made = models.BooleanField(default=False)
    adjustment_details = models.TextField(blank=True)

    # Acceptance criteria
    acceptance_criteria = models.JSONField(
        default=dict,
        help_text='Calibration acceptance criteria'
    )

    # Next calibration
    next_calibration_date = models.DateField()

    # Certificate
    certificate_number = models.CharField(max_length=100, blank=True)
    certificate_file = models.FileField(
        upload_to='calibration_certs/%Y/%m/',
        blank=True,
        null=True
    )

    # Reviewer
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_calibrations'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'manufacturing_calibration_records'
        ordering = ['-calibration_date']

    def __str__(self):
        return f'{self.equipment.equipment_id} - {self.calibration_date}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update equipment calibration dates
        self.equipment.last_calibration_date = self.calibration_date
        self.equipment.next_calibration_date = self.next_calibration_date
        self.equipment.save(update_fields=[
            'last_calibration_date',
            'next_calibration_date'
        ])


class EquipmentUsage(AuditableModel):
    """
    Record of equipment usage in production.
    """

    # Equipment reference
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='usage_records'
    )

    # Batch reference
    batch = models.ForeignKey(
        'batch_records.Batch',
        on_delete=models.PROTECT,
        related_name='equipment_usages'
    )
    batch_step = models.ForeignKey(
        'batch_records.BatchStep',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipment_usages'
    )

    # Usage details
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    operated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='equipment_operations'
    )

    # Pre-use verification
    pre_use_check_completed = models.BooleanField(default=False)
    calibration_verified = models.BooleanField(default=False)
    equipment_clean = models.BooleanField(default=False)

    # Operating parameters recorded
    parameters_recorded = models.JSONField(
        default=dict,
        help_text='Operating parameters used/recorded'
    )

    # Barcode scanning
    equipment_barcode_scanned = models.BooleanField(default=False)

    # Post-use
    cleaning_required = models.BooleanField(default=True)
    cleaning_completed = models.BooleanField(default=False)
    cleaning_completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipment_cleanings'
    )
    cleaning_completed_at = models.DateTimeField(null=True, blank=True)

    # Issues
    issues_encountered = models.BooleanField(default=False)
    issue_details = models.TextField(blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'manufacturing_equipment_usage'
        ordering = ['-start_time']

    def __str__(self):
        return f'{self.equipment.equipment_id} - {self.batch.batch_number}'

    @property
    def duration(self):
        """Calculate usage duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
