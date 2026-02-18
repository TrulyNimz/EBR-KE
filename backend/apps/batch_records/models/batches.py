"""
Batch Record models for the EBR Platform.

Core models for managing batch records across all industry modules.
"""
import uuid
import hashlib
import json
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from apps.core.models import AuditableModel


class Batch(AuditableModel):
    """
    A batch represents a production lot or record container.

    Batches contain multiple batch records (steps) and track
    overall completion status.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        IN_PROGRESS = 'in_progress', 'In Progress'
        PENDING_REVIEW = 'pending_review', 'Pending Review'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    # Unique batch number (generated or manual)
    batch_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Unique batch identifier'
    )

    # Basic info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Product/Template reference
    product_code = models.CharField(
        max_length=100,
        blank=True,
        help_text='Product code this batch is for'
    )
    product_name = models.CharField(max_length=255, blank=True)
    template = models.ForeignKey(
        'BatchTemplate',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='batches',
        help_text='Template used to create this batch'
    )

    # Status and priority
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL
    )

    # Workflow integration
    workflow_instance = models.ForeignKey(
        'workflow.WorkflowInstance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batches'
    )

    # Timing
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    # Quantity tracking
    planned_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    actual_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    quantity_unit = models.CharField(max_length=50, blank=True)

    # Industry module type
    module_type = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text='Industry module (healthcare, manufacturing, agriculture)'
    )

    # Custom data (flexible JSON storage)
    custom_data = models.JSONField(
        default=dict,
        help_text='Additional module-specific data'
    )

    # Digital signatures (via GenericRelation)
    signatures = GenericRelation(
        'audit.DigitalSignature',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    # Audit logs
    audit_logs = GenericRelation(
        'audit.AuditLog',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'batches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'batch_number']),
            models.Index(fields=['module_type', 'status']),
        ]

    def __str__(self):
        return f'{self.batch_number} - {self.name}'

    def _get_checksum_fields(self):
        """Fields to include in integrity checksum."""
        return {
            'batch_number': self.batch_number,
            'name': self.name,
            'product_code': self.product_code,
            'status': self.status,
            'planned_quantity': str(self.planned_quantity) if self.planned_quantity else None,
            'actual_quantity': str(self.actual_quantity) if self.actual_quantity else None,
        }

    @property
    def completion_percentage(self):
        """Calculate completion percentage based on steps."""
        steps = self.steps.all()
        if not steps.exists():
            return 0
        completed = steps.filter(status=BatchStep.Status.COMPLETED).count()
        return int((completed / steps.count()) * 100)

    @property
    def is_complete(self):
        """Check if all steps are completed."""
        return self.completion_percentage == 100

    def start(self, user):
        """Start the batch execution."""
        from django.utils import timezone
        if self.status != self.Status.DRAFT:
            raise ValueError('Batch can only be started from draft status')
        self.status = self.Status.IN_PROGRESS
        self.actual_start = timezone.now()
        self.save(update_fields=['status', 'actual_start', 'modified_at', 'modified_by'])

    def complete(self, user):
        """Mark the batch as completed."""
        from django.utils import timezone
        if not self.is_complete:
            raise ValueError('Cannot complete batch with incomplete steps')
        self.status = self.Status.COMPLETED
        self.actual_end = timezone.now()
        self.save(update_fields=['status', 'actual_end', 'modified_at', 'modified_by'])


class BatchTemplate(AuditableModel):
    """
    Template for creating batch records.

    Defines the structure (steps) and default values for batches.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        DEPRECATED = 'deprecated', 'Deprecated'
        ARCHIVED = 'archived', 'Archived'

    # Basic info
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Version control
    version = models.PositiveIntegerField(default=1)
    parent_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_versions'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # Product reference
    product_code = models.CharField(max_length=100, blank=True)
    product_name = models.CharField(max_length=255, blank=True)

    # Associated workflow
    workflow = models.ForeignKey(
        'workflow.WorkflowDefinition',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batch_templates'
    )

    # Module type
    module_type = models.CharField(max_length=50, blank=True)

    # Default values
    default_quantity_unit = models.CharField(max_length=50, blank=True)
    default_custom_data = models.JSONField(default=dict)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'batch_templates'
        ordering = ['name', '-version']
        unique_together = ['code', 'version', 'tenant_id']

    def __str__(self):
        return f'{self.name} v{self.version}'

    def create_batch(self, user, batch_number, **kwargs):
        """Create a new batch from this template."""
        batch = Batch.objects.create(
            batch_number=batch_number,
            name=kwargs.get('name', self.name),
            description=kwargs.get('description', self.description),
            product_code=self.product_code,
            product_name=self.product_name,
            template=self,
            module_type=self.module_type,
            quantity_unit=self.default_quantity_unit,
            custom_data=self.default_custom_data.copy(),
            tenant_id=self.tenant_id,
            created_by=user,
            **{k: v for k, v in kwargs.items() if k not in ['name', 'description']}
        )

        # Create steps from template
        for step_template in self.step_templates.all():
            step_template.create_step(batch, user)

        return batch


class BatchStep(AuditableModel):
    """
    A step within a batch record.

    Steps represent individual operations or data collection points.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        SKIPPED = 'skipped', 'Skipped'
        FAILED = 'failed', 'Failed'

    class StepType(models.TextChoices):
        DATA_ENTRY = 'data_entry', 'Data Entry'
        VERIFICATION = 'verification', 'Verification'
        APPROVAL = 'approval', 'Approval'
        SIGNATURE = 'signature', 'Signature Required'
        ATTACHMENT = 'attachment', 'Attachment Required'
        CALCULATION = 'calculation', 'Calculation'
        INSTRUCTION = 'instruction', 'Instruction'

    # Parent batch
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='steps'
    )

    # Step template reference
    template = models.ForeignKey(
        'BatchStepTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instances'
    )

    # Basic info
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)

    # Ordering
    sequence = models.PositiveIntegerField(default=0)

    # Step type and status
    step_type = models.CharField(
        max_length=20,
        choices=StepType.choices,
        default=StepType.DATA_ENTRY
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Form schema (JSON Schema format)
    form_schema = models.JSONField(
        null=True,
        blank=True,
        help_text='JSON Schema for data entry form'
    )

    # Collected data
    data = models.JSONField(
        default=dict,
        help_text='Data collected/entered for this step'
    )

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Who executed
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='executed_steps'
    )

    # Verification
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='verified_steps'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Deviation/exception handling
    has_deviation = models.BooleanField(default=False)
    deviation_notes = models.TextField(blank=True)

    # Dependencies
    depends_on = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='dependents'
    )

    # Digital signatures
    signatures = GenericRelation(
        'audit.DigitalSignature',
        content_type_field='content_type',
        object_id_field='object_id'
    )

    class Meta:
        db_table = 'batch_steps'
        ordering = ['batch', 'sequence']
        unique_together = ['batch', 'code']

    def __str__(self):
        return f'{self.batch.batch_number} - {self.name}'

    def _get_checksum_fields(self):
        """Fields to include in integrity checksum."""
        return {
            'batch_id': str(self.batch_id),
            'code': self.code,
            'status': self.status,
            'data': json.dumps(self.data, sort_keys=True, default=str),
            'has_deviation': self.has_deviation,
        }

    @property
    def can_start(self):
        """Check if this step can be started."""
        if self.status != self.Status.PENDING:
            return False
        # Check dependencies
        for dep in self.depends_on.all():
            if dep.status != self.Status.COMPLETED:
                return False
        return True

    def start(self, user):
        """Start executing this step."""
        from django.utils import timezone
        if not self.can_start:
            raise ValueError('Step cannot be started (check dependencies and status)')
        self.status = self.Status.IN_PROGRESS
        self.started_at = timezone.now()
        self.executed_by = user
        self.save(update_fields=['status', 'started_at', 'executed_by', 'modified_at', 'modified_by'])

    def complete(self, user, data=None):
        """Complete this step with optional data."""
        from django.utils import timezone
        if self.status != self.Status.IN_PROGRESS:
            raise ValueError('Step must be in progress to complete')
        if data:
            self.data = data
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'data', 'completed_at', 'modified_at', 'modified_by'])


class BatchStepTemplate(AuditableModel):
    """
    Template for batch steps.

    Defines default configuration for steps within a batch template.
    """

    # Parent template
    batch_template = models.ForeignKey(
        BatchTemplate,
        on_delete=models.CASCADE,
        related_name='step_templates'
    )

    # Basic info
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)

    # Ordering
    sequence = models.PositiveIntegerField(default=0)

    # Step type
    step_type = models.CharField(
        max_length=20,
        choices=BatchStep.StepType.choices,
        default=BatchStep.StepType.DATA_ENTRY
    )

    # Form schema
    form_schema = models.JSONField(
        null=True,
        blank=True,
        help_text='JSON Schema for data entry form'
    )

    # Requirements
    requires_verification = models.BooleanField(default=False)
    requires_signature = models.BooleanField(default=False)
    signature_meaning = models.CharField(
        max_length=50,
        blank=True,
        help_text='Signature meaning code if signature required'
    )

    # Role requirements
    required_role = models.CharField(
        max_length=100,
        blank=True,
        help_text='Role code required to execute this step'
    )
    verifier_role = models.CharField(
        max_length=100,
        blank=True,
        help_text='Role code required to verify this step'
    )

    # Workflow state mapping
    workflow_state = models.CharField(
        max_length=100,
        blank=True,
        help_text='Workflow state this step corresponds to'
    )

    # Default values
    default_data = models.JSONField(default=dict)

    class Meta:
        db_table = 'batch_step_templates'
        ordering = ['batch_template', 'sequence']
        unique_together = ['batch_template', 'code']

    def __str__(self):
        return f'{self.batch_template.name} - {self.name}'

    def create_step(self, batch, user):
        """Create a batch step from this template."""
        return BatchStep.objects.create(
            batch=batch,
            template=self,
            code=self.code,
            name=self.name,
            description=self.description,
            instructions=self.instructions,
            sequence=self.sequence,
            step_type=self.step_type,
            form_schema=self.form_schema,
            data=self.default_data.copy(),
            created_by=user
        )


class BatchAttachment(AuditableModel):
    """
    File attachment for a batch or batch step.
    """

    class AttachmentType(models.TextChoices):
        DOCUMENT = 'document', 'Document'
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        SIGNATURE = 'signature', 'Signature Image'
        LAB_RESULT = 'lab_result', 'Lab Result'
        CERTIFICATE = 'certificate', 'Certificate'
        OTHER = 'other', 'Other'

    # Parent (batch or step)
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    step = models.ForeignKey(
        BatchStep,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments'
    )

    # File info
    file = models.FileField(upload_to='batch_attachments/%Y/%m/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text='Size in bytes')
    content_type = models.CharField(max_length=100)
    attachment_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
        default=AttachmentType.DOCUMENT
    )

    # Metadata
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    # Version control
    version = models.PositiveIntegerField(default=1)
    replaces = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replaced_by'
    )

    # Integrity
    file_hash = models.CharField(
        max_length=64,
        help_text='SHA-256 hash of file contents'
    )

    class Meta:
        db_table = 'batch_attachments'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.batch.batch_number} - {self.filename}'

    def save(self, *args, **kwargs):
        # Calculate file hash if not set
        if self.file and not self.file_hash:
            hasher = hashlib.sha256()
            for chunk in self.file.chunks():
                hasher.update(chunk)
            self.file_hash = hasher.hexdigest()
        super().save(*args, **kwargs)
