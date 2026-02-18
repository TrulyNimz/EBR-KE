"""
Manufacturing Raw Material models.

Tracks raw materials, suppliers, and material lots for
pharmaceutical and industrial manufacturing.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditableModel


class RawMaterial(AuditableModel):
    """
    Raw material catalog entry.
    """

    class MaterialType(models.TextChoices):
        ACTIVE_INGREDIENT = 'active', 'Active Ingredient'
        EXCIPIENT = 'excipient', 'Excipient'
        PACKAGING = 'packaging', 'Packaging Material'
        CONSUMABLE = 'consumable', 'Consumable'
        OTHER = 'other', 'Other'

    class StorageClass(models.TextChoices):
        AMBIENT = 'ambient', 'Ambient (15-25°C)'
        REFRIGERATED = 'refrigerated', 'Refrigerated (2-8°C)'
        FROZEN = 'frozen', 'Frozen (-20°C)'
        CONTROLLED = 'controlled', 'Controlled Substance'
        HAZARDOUS = 'hazardous', 'Hazardous Material'

    # Identification
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Classification
    material_type = models.CharField(
        max_length=20,
        choices=MaterialType.choices,
        default=MaterialType.OTHER
    )

    # Specifications
    cas_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Chemical Abstracts Service number'
    )
    specifications = models.JSONField(
        default=dict,
        help_text='Material specifications and limits'
    )

    # Storage requirements
    storage_class = models.CharField(
        max_length=20,
        choices=StorageClass.choices,
        default=StorageClass.AMBIENT
    )
    storage_conditions = models.TextField(blank=True)
    shelf_life_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Shelf life in days'
    )

    # Reorder settings
    reorder_point = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    reorder_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    unit_of_measure = models.CharField(max_length=20)

    # Safety information
    msds_available = models.BooleanField(default=False)
    safety_precautions = models.TextField(blank=True)
    ppe_required = models.JSONField(
        default=list,
        help_text='Required personal protective equipment'
    )

    # Status
    is_active = models.BooleanField(default=True)
    requires_coa = models.BooleanField(
        default=True,
        help_text='Requires Certificate of Analysis'
    )

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'manufacturing_raw_materials'
        ordering = ['name']

    def __str__(self):
        return f'{self.code} - {self.name}'


class Supplier(AuditableModel):
    """
    Supplier/vendor information.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Approval'
        APPROVED = 'approved', 'Approved'
        SUSPENDED = 'suspended', 'Suspended'
        DISQUALIFIED = 'disqualified', 'Disqualified'

    # Identification
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)

    # Contact information
    contact_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    approved_date = models.DateField(null=True, blank=True)
    next_audit_date = models.DateField(null=True, blank=True)

    # Certifications
    certifications = models.JSONField(
        default=list,
        help_text='List of certifications (ISO, GMP, etc.)'
    )

    # Performance metrics
    quality_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Quality rating (0-5)'
    )
    delivery_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Delivery rating (0-5)'
    )

    # Materials supplied
    materials = models.ManyToManyField(
        RawMaterial,
        related_name='suppliers',
        blank=True
    )

    # Notes
    notes = models.TextField(blank=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'manufacturing_suppliers'
        ordering = ['name']

    def __str__(self):
        return f'{self.code} - {self.name}'


class MaterialLot(AuditableModel):
    """
    Received lot of raw material.

    Tracks individual receipts with full traceability.
    """

    class Status(models.TextChoices):
        QUARANTINE = 'quarantine', 'Quarantine'
        PENDING_QC = 'pending_qc', 'Pending QC'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        EXPIRED = 'expired', 'Expired'
        CONSUMED = 'consumed', 'Consumed'

    # Material reference
    material = models.ForeignKey(
        RawMaterial,
        on_delete=models.PROTECT,
        related_name='lots'
    )

    # Lot identification
    lot_number = models.CharField(max_length=100, db_index=True)
    supplier_lot_number = models.CharField(max_length=100, blank=True)
    internal_lot_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True
    )

    # Supplier and receipt
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='material_lots'
    )
    received_date = models.DateField()
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='received_lots'
    )
    purchase_order = models.CharField(max_length=100, blank=True)

    # Quantity
    quantity_received = models.DecimalField(max_digits=15, decimal_places=4)
    quantity_available = models.DecimalField(max_digits=15, decimal_places=4)
    unit_of_measure = models.CharField(max_length=20)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUARANTINE
    )

    # Dates
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    retest_date = models.DateField(null=True, blank=True)

    # Certificate of Analysis
    coa_received = models.BooleanField(default=False)
    coa_file = models.FileField(
        upload_to='coa/%Y/%m/',
        blank=True,
        null=True
    )

    # Storage location
    storage_location = models.CharField(max_length=100, blank=True)
    storage_conditions = models.CharField(max_length=200, blank=True)

    # QC information
    qc_sample_taken = models.BooleanField(default=False)
    qc_sample_date = models.DateTimeField(null=True, blank=True)
    qc_approved_date = models.DateTimeField(null=True, blank=True)
    qc_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_lots'
    )

    # Notes
    notes = models.TextField(blank=True)

    # Barcode
    barcode = models.CharField(max_length=100, blank=True, db_index=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'manufacturing_material_lots'
        ordering = ['-received_date']
        unique_together = ['material', 'lot_number', 'tenant_id']

    def __str__(self):
        return f'{self.material.code} - {self.lot_number}'

    @property
    def is_expired(self):
        """Check if lot is expired."""
        from datetime import date
        if self.expiry_date:
            return date.today() > self.expiry_date
        return False

    @property
    def days_until_expiry(self):
        """Days until expiry."""
        from datetime import date
        if self.expiry_date:
            delta = self.expiry_date - date.today()
            return delta.days
        return None


class MaterialUsage(AuditableModel):
    """
    Record of material usage in production.

    Provides full traceability from raw material to finished batch.
    """

    # Lot reference
    lot = models.ForeignKey(
        MaterialLot,
        on_delete=models.PROTECT,
        related_name='usages'
    )

    # Batch reference
    batch = models.ForeignKey(
        'batch_records.Batch',
        on_delete=models.PROTECT,
        related_name='material_usages'
    )
    batch_step = models.ForeignKey(
        'batch_records.BatchStep',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='material_usages'
    )

    # Usage details
    quantity_used = models.DecimalField(max_digits=15, decimal_places=4)
    unit_of_measure = models.CharField(max_length=20)
    used_at = models.DateTimeField()
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='material_usages'
    )

    # Verification
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_material_usages'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Barcode scanning
    lot_barcode_scanned = models.BooleanField(default=False)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'manufacturing_material_usages'
        ordering = ['-used_at']

    def __str__(self):
        return f'{self.lot.internal_lot_number} -> {self.batch.batch_number}'

    def save(self, *args, **kwargs):
        # Deduct from available quantity
        if not self.pk:  # New record
            if self.lot.quantity_available < self.quantity_used:
                raise ValueError('Insufficient quantity available')
            self.lot.quantity_available -= self.quantity_used
            self.lot.save(update_fields=['quantity_available'])
        super().save(*args, **kwargs)
