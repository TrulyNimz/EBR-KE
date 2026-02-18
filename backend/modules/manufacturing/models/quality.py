"""
Manufacturing Quality Control models.

QC testing, results, and release decisions.
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from apps.core.models import AuditableModel


class QCTest(AuditableModel):
    """
    Quality Control test definition.
    """

    class TestType(models.TextChoices):
        CHEMICAL = 'chemical', 'Chemical Analysis'
        PHYSICAL = 'physical', 'Physical Test'
        MICROBIOLOGICAL = 'microbiological', 'Microbiological'
        DISSOLUTION = 'dissolution', 'Dissolution'
        STABILITY = 'stability', 'Stability'
        OTHER = 'other', 'Other'

    # Identification
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Classification
    test_type = models.CharField(
        max_length=20,
        choices=TestType.choices,
        default=TestType.OTHER
    )

    # Test method
    method_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text='e.g., USP method, in-house method number'
    )
    method_description = models.TextField(blank=True)

    # Acceptance criteria
    specification = models.JSONField(
        default=dict,
        help_text='Test specifications and limits'
    )

    # Result type
    result_type = models.CharField(
        max_length=20,
        default='numeric',
        help_text='numeric, text, pass_fail'
    )
    unit_of_measure = models.CharField(max_length=50, blank=True)

    # Timing
    typical_duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Equipment required
    required_equipment = models.ManyToManyField(
        'manufacturing.Equipment',
        blank=True,
        related_name='qc_tests'
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'manufacturing_qc_tests'
        ordering = ['name']

    def __str__(self):
        return f'{self.code} - {self.name}'


class QCTestRequest(AuditableModel):
    """
    Request for QC testing on a sample.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class SampleType(models.TextChoices):
        RAW_MATERIAL = 'raw_material', 'Raw Material'
        IN_PROCESS = 'in_process', 'In-Process'
        FINISHED_PRODUCT = 'finished_product', 'Finished Product'
        STABILITY = 'stability', 'Stability Sample'
        ENVIRONMENTAL = 'environmental', 'Environmental'

    # Request identification
    request_number = models.CharField(max_length=50, unique=True, db_index=True)

    # Sample information
    sample_type = models.CharField(
        max_length=20,
        choices=SampleType.choices
    )
    sample_description = models.CharField(max_length=255)
    sample_quantity = models.CharField(max_length=100)

    # Reference to source
    batch = models.ForeignKey(
        'batch_records.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qc_requests'
    )
    material_lot = models.ForeignKey(
        'manufacturing.MaterialLot',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qc_requests'
    )

    # Tests requested
    tests = models.ManyToManyField(QCTest, related_name='requests')

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Requester
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='qc_requests'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(
        max_length=20,
        default='normal',
        help_text='normal, urgent, rush'
    )

    # Timing
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'manufacturing_qc_requests'
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.request_number} - {self.sample_description}'


class QCResult(AuditableModel):
    """
    Individual QC test result.
    """

    class Outcome(models.TextChoices):
        PASS = 'pass', 'Pass'
        FAIL = 'fail', 'Fail'
        PENDING = 'pending', 'Pending Review'
        INCONCLUSIVE = 'inconclusive', 'Inconclusive'

    # Test request reference
    request = models.ForeignKey(
        QCTestRequest,
        on_delete=models.CASCADE,
        related_name='results'
    )

    # Test reference
    test = models.ForeignKey(
        QCTest,
        on_delete=models.PROTECT,
        related_name='results'
    )

    # Result data
    result_value = models.CharField(max_length=255, blank=True)
    result_numeric = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True
    )
    result_unit = models.CharField(max_length=50, blank=True)
    result_data = models.JSONField(
        default=dict,
        help_text='Additional result data'
    )

    # Outcome
    outcome = models.CharField(
        max_length=20,
        choices=Outcome.choices,
        default=Outcome.PENDING
    )

    # Specification comparison
    specification_used = models.JSONField(
        default=dict,
        help_text='Specification applied at time of testing'
    )
    within_specification = models.BooleanField(null=True)

    # Analyst
    tested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='qc_results'
    )
    tested_at = models.DateTimeField()

    # Equipment used
    equipment_used = models.ManyToManyField(
        'manufacturing.Equipment',
        blank=True,
        related_name='qc_results'
    )

    # Reviewer
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_qc_results'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Retest information
    is_retest = models.BooleanField(default=False)
    retest_reason = models.TextField(blank=True)
    original_result = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='retests'
    )

    # Digital signatures
    signatures = GenericRelation(
        'audit.DigitalSignature',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'manufacturing_qc_results'
        ordering = ['-tested_at']

    def __str__(self):
        return f'{self.request.request_number} - {self.test.name}'


class BatchRelease(AuditableModel):
    """
    Batch release decision.

    Final QA release of a batch for distribution.
    """

    class Decision(models.TextChoices):
        RELEASED = 'released', 'Released'
        REJECTED = 'rejected', 'Rejected'
        QUARANTINE = 'quarantine', 'Quarantine'
        REWORK = 'rework', 'Rework Required'

    # Batch reference
    batch = models.OneToOneField(
        'batch_records.Batch',
        on_delete=models.PROTECT,
        related_name='release_record'
    )

    # Decision
    decision = models.CharField(
        max_length=20,
        choices=Decision.choices
    )
    decision_date = models.DateTimeField()
    decision_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='batch_releases'
    )

    # Review checklist
    manufacturing_record_reviewed = models.BooleanField(default=False)
    qc_results_reviewed = models.BooleanField(default=False)
    deviations_reviewed = models.BooleanField(default=False)
    specifications_met = models.BooleanField(default=False)

    # Deviations
    has_deviations = models.BooleanField(default=False)
    deviation_summary = models.TextField(blank=True)
    deviations_acceptable = models.BooleanField(null=True)

    # Comments
    comments = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    # Certificate of Analysis
    coa_generated = models.BooleanField(default=False)
    coa_file = models.FileField(
        upload_to='batch_coa/%Y/%m/',
        blank=True,
        null=True
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
        db_table = 'manufacturing_batch_releases'
        ordering = ['-decision_date']

    def __str__(self):
        return f'{self.batch.batch_number} - {self.decision}'
