"""
Digital Signature models for FDA 21 CFR Part 11 compliance.

Electronic signatures that are unique to an individual,
linked to the electronic record, and include the meaning of the signature.
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from services.encryption.signature_service import SignatureService


class SignatureMeaning(models.Model):
    """
    Predefined signature meanings per FDA 21 CFR Part 11.

    Examples: Approved, Reviewed, Verified, Rejected, Witnessed
    """

    code = models.CharField(max_length=50, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    requires_comment = models.BooleanField(
        default=False,
        help_text='Require signer to provide comment'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'signature_meanings'
        verbose_name_plural = 'Signature meanings'

    def __str__(self):
        return self.name


class DigitalSignature(models.Model):
    """
    Digital signature record.

    Immutable record of a digital signature applied to an electronic record.
    Contains cryptographic proof of the signer's identity and intent.
    """

    class Status(models.TextChoices):
        VALID = 'valid', 'Valid'
        REVOKED = 'revoked', 'Revoked'
        EXPIRED = 'expired', 'Expired'

    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Timestamp
    signed_at = models.DateTimeField(auto_now_add=True)

    # Signer information
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='digital_signatures'
    )
    signer_email = models.EmailField(
        help_text='Stored separately for compliance records'
    )
    signer_full_name = models.CharField(max_length=255)
    signer_employee_id = models.CharField(max_length=100, blank=True)

    # Signature meaning
    meaning = models.ForeignKey(
        SignatureMeaning,
        on_delete=models.PROTECT,
        related_name='signatures'
    )
    meaning_text = models.CharField(
        max_length=255,
        help_text='Full text shown to signer at signing time'
    )
    signer_comment = models.TextField(
        blank=True,
        help_text='Optional comment from signer'
    )

    # Signed record (generic foreign key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT
    )
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Additional record identifiers
    record_type = models.CharField(max_length=100)
    record_identifier = models.CharField(
        max_length=255,
        help_text='Human-readable identifier (e.g., batch number)'
    )

    # Cryptographic signature
    data_hash = models.CharField(
        max_length=64,
        help_text='SHA-256 hash of the signed data'
    )
    signature_value = models.TextField(
        help_text='Base64-encoded cryptographic signature'
    )
    signature_algorithm = models.CharField(
        max_length=50,
        default='RSA-PSS-SHA256'
    )

    # Signature manifest (JSON containing full signature details)
    signature_manifest = models.JSONField(
        help_text='Complete signature data for verification'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.VALID
    )
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='signature_status_changes'
    )
    status_change_reason = models.TextField(blank=True)

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Tenant context
    tenant_id = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'digital_signatures'
        ordering = ['-signed_at']
        indexes = [
            models.Index(fields=['signer', 'signed_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['record_type', 'record_identifier']),
            models.Index(fields=['status', 'signed_at']),
        ]

    def __str__(self):
        return f'{self.signer_email} - {self.meaning.name} - {self.record_identifier}'

    def save(self, *args, **kwargs):
        """Prevent modification of existing signatures."""
        if self.pk and DigitalSignature.objects.filter(pk=self.pk).exists():
            existing = DigitalSignature.objects.get(pk=self.pk)
            # Only allow status changes
            allowed_fields = {'status', 'status_changed_at', 'status_changed_by', 'status_change_reason'}
            for field in self._meta.fields:
                if field.name not in allowed_fields and field.name != 'id':
                    if getattr(self, field.name) != getattr(existing, field.name):
                        raise PermissionError('Digital signatures cannot be modified.')
        super().save(*args, **kwargs)

    def verify(self):
        """
        Verify the signature is valid.

        Returns True if the cryptographic signature is valid.
        """
        if not self.signer.signature_public_key:
            return False

        return SignatureService.verify_signature(
            public_key_pem=self.signer.signature_public_key,
            signature_data=self.signature_manifest
        )

    @classmethod
    def create_signature(
        cls,
        signer,
        meaning_code,
        record,
        record_data,
        comment='',
        ip_address=None,
        user_agent='',
        tenant_id=''
    ):
        """
        Create a new digital signature for a record.

        Args:
            signer: The User signing the record.
            meaning_code: The SignatureMeaning code (e.g., 'approval').
            record: The Django model instance being signed.
            record_data: Dictionary of data to include in signature.
            comment: Optional comment from the signer.
            ip_address: Client IP address.
            user_agent: Client user agent.
            tenant_id: Current tenant ID.

        Returns:
            The created DigitalSignature instance.
        """
        # Verify signer has signing keys
        if not signer.signature_private_key or not signer.digital_signature_enabled:
            raise ValueError('Signer does not have digital signature enabled.')

        # Get signature meaning
        try:
            meaning = SignatureMeaning.objects.get(code=meaning_code, is_active=True)
        except SignatureMeaning.DoesNotExist:
            raise ValueError(f'Invalid signature meaning: {meaning_code}')

        # Check if comment is required
        if meaning.requires_comment and not comment:
            raise ValueError('Comment is required for this signature type.')

        # Get content type for the record
        content_type = ContentType.objects.get_for_model(record)

        # Create cryptographic signature
        signature_data = SignatureService.sign_data(
            private_key_pem=signer.signature_private_key,
            data=record_data,
            signer_id=str(signer.id),
            signer_name=signer.full_name,
            signature_meaning=meaning_code
        )

        # Get record identifier (use common attribute names)
        record_identifier = (
            getattr(record, 'batch_number', None) or
            getattr(record, 'identifier', None) or
            getattr(record, 'code', None) or
            str(record.pk)
        )

        # Create signature record
        signature = cls.objects.create(
            signer=signer,
            signer_email=signer.email,
            signer_full_name=signer.full_name,
            signer_employee_id=getattr(signer, 'employee_id', ''),
            meaning=meaning,
            meaning_text=f'{meaning.name}: {meaning.description}',
            signer_comment=comment,
            content_type=content_type,
            object_id=str(record.pk),
            record_type=content_type.model,
            record_identifier=record_identifier,
            data_hash=signature_data['payload']['data_hash'],
            signature_value=signature_data['signature'],
            signature_algorithm=signature_data['algorithm'],
            signature_manifest=signature_data,
            ip_address=ip_address,
            user_agent=user_agent,
            tenant_id=tenant_id
        )

        return signature

    @classmethod
    def get_signatures_for_record(cls, record):
        """Get all valid signatures for a record."""
        content_type = ContentType.objects.get_for_model(record)
        return cls.objects.filter(
            content_type=content_type,
            object_id=str(record.pk),
            status=cls.Status.VALID
        ).select_related('signer', 'meaning')


class SignatureRequirement(models.Model):
    """
    Defines signature requirements for record types.

    Specifies what signatures are required before a record
    can be considered complete or approved.
    """

    # What record type this applies to
    record_type = models.CharField(max_length=100)

    # What workflow state this applies to (optional)
    workflow_state = models.CharField(max_length=100, blank=True)

    # Required signature meaning
    required_meaning = models.ForeignKey(
        SignatureMeaning,
        on_delete=models.PROTECT
    )

    # How many signatures of this type are required
    min_signatures = models.PositiveIntegerField(default=1)

    # Role required for this signature (optional)
    required_role = models.CharField(
        max_length=100,
        blank=True,
        help_text='Role code required for this signature'
    )

    # Order in which signatures should be collected
    order = models.PositiveIntegerField(default=0)

    # Is this requirement active?
    is_active = models.BooleanField(default=True)

    # Tenant (empty for global requirements)
    tenant_id = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'signature_requirements'
        ordering = ['record_type', 'order']
        unique_together = ['record_type', 'workflow_state', 'required_meaning', 'tenant_id']

    def __str__(self):
        return f'{self.record_type} - {self.required_meaning.name} ({self.min_signatures}x)'

    @classmethod
    def check_requirements(cls, record, workflow_state=''):
        """
        Check if a record meets all signature requirements.

        Returns:
            Tuple of (is_complete, missing_requirements)
        """
        content_type = ContentType.objects.get_for_model(record)
        record_type = content_type.model

        requirements = cls.objects.filter(
            record_type=record_type,
            workflow_state=workflow_state,
            is_active=True
        ).select_related('required_meaning')

        missing = []

        for req in requirements:
            signature_count = DigitalSignature.objects.filter(
                content_type=content_type,
                object_id=str(record.pk),
                meaning=req.required_meaning,
                status=DigitalSignature.Status.VALID
            ).count()

            if signature_count < req.min_signatures:
                missing.append({
                    'meaning': req.required_meaning.name,
                    'required': req.min_signatures,
                    'current': signature_count,
                    'required_role': req.required_role
                })

        return len(missing) == 0, missing
