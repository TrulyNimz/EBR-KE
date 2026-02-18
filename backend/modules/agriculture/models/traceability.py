"""
Agriculture Traceability models.

Chain of custody tracking from farm to consumer.
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.core.models import AuditableModel


class TraceabilityRecord(AuditableModel):
    """
    Chain of custody record.

    Tracks the movement of agricultural products through
    the supply chain with full traceability.
    """

    class EventType(models.TextChoices):
        HARVEST = 'harvest', 'Harvest'
        STORAGE = 'storage', 'Storage'
        PROCESSING = 'processing', 'Processing'
        PACKAGING = 'packaging', 'Packaging'
        TRANSPORT = 'transport', 'Transport'
        DELIVERY = 'delivery', 'Delivery'
        SALE = 'sale', 'Sale'
        QUALITY_CHECK = 'quality_check', 'Quality Check'
        TRANSFORMATION = 'transformation', 'Transformation'

    # Traceability identification
    trace_code = models.CharField(max_length=100, unique=True, db_index=True)

    # Source reference (generic - can be crop batch, animal, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT
    )
    object_id = models.CharField(max_length=255)
    source_object = GenericForeignKey('content_type', 'object_id')

    # Event information
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices
    )
    event_date = models.DateTimeField()
    event_location = models.CharField(max_length=255)

    # GPS coordinates
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    # Quantity and product
    product_description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    unit = models.CharField(max_length=20)

    # Quality information
    quality_grade = models.CharField(max_length=50, blank=True)
    quality_parameters = models.JSONField(
        default=dict,
        help_text='Quality measurements'
    )

    # Chain links
    previous_record = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='next_records'
    )

    # Parties involved
    from_party = models.CharField(max_length=255, blank=True)
    to_party = models.CharField(max_length=255, blank=True)

    # Certifications
    certifications = models.JSONField(
        default=list,
        help_text='Applicable certifications (organic, fair trade, etc.)'
    )

    # Documents
    documents = models.JSONField(
        default=list,
        help_text='Related document references'
    )

    # Handler
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='traceability_records'
    )

    # Verified
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_traceability_records'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Blockchain hash (for advanced traceability)
    blockchain_hash = models.CharField(max_length=128, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'agriculture_traceability_records'
        ordering = ['-event_date']

    def __str__(self):
        return f'{self.trace_code} - {self.event_type}'

    def get_full_chain(self):
        """Get the complete traceability chain for this product."""
        chain = [self]
        current = self.previous_record

        while current:
            chain.insert(0, current)
            current = current.previous_record

        return chain

    @classmethod
    def get_chain_for_product(cls, trace_code):
        """Get the traceability chain starting from any point."""
        try:
            record = cls.objects.get(trace_code=trace_code)
            return record.get_full_chain()
        except cls.DoesNotExist:
            return []


class CertificationRecord(AuditableModel):
    """
    Certification record for farms, fields, or products.
    """

    class CertificationType(models.TextChoices):
        ORGANIC = 'organic', 'Organic'
        FAIR_TRADE = 'fair_trade', 'Fair Trade'
        RAINFOREST = 'rainforest', 'Rainforest Alliance'
        GAP = 'gap', 'Good Agricultural Practices'
        HACCP = 'haccp', 'HACCP'
        ISO = 'iso', 'ISO'
        OTHER = 'other', 'Other'

    # Certification details
    certification_type = models.CharField(
        max_length=20,
        choices=CertificationType.choices
    )
    certification_name = models.CharField(max_length=255)
    certifying_body = models.CharField(max_length=255)
    certificate_number = models.CharField(max_length=100)

    # Validity
    issued_date = models.DateField()
    expiry_date = models.DateField()
    is_valid = models.BooleanField(default=True)

    # Scope
    scope_description = models.TextField(blank=True)

    # Certificate document
    certificate_file = models.FileField(
        upload_to='certifications/%Y/%m/',
        blank=True,
        null=True
    )

    # Related entity (generic)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.CharField(max_length=255)
    certified_entity = GenericForeignKey('content_type', 'object_id')

    # Audits
    last_audit_date = models.DateField(null=True, blank=True)
    next_audit_date = models.DateField(null=True, blank=True)
    audit_notes = models.TextField(blank=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'agriculture_certifications'
        ordering = ['-issued_date']

    def __str__(self):
        return f'{self.certification_name} - {self.certificate_number}'

    @property
    def days_until_expiry(self):
        """Days until certification expires."""
        from datetime import date
        delta = self.expiry_date - date.today()
        return delta.days

    @property
    def is_expired(self):
        """Check if certification is expired."""
        from datetime import date
        return date.today() > self.expiry_date
