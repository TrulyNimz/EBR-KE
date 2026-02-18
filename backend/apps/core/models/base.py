"""
Base models for the EBR Platform.

All auditable models inherit from these base classes to ensure
consistent behavior across the application.
"""
import uuid
import hashlib
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model with automatic timestamps.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract base model with UUID primary key.
    Provides globally unique identifiers for all records.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """
    Manager that filters out soft-deleted records by default.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        """Return all records including soft-deleted ones."""
        return super().get_queryset()

    def deleted_only(self):
        """Return only soft-deleted records."""
        return super().get_queryset().filter(is_deleted=True)


class SoftDeleteModel(models.Model):
    """
    Abstract base model for soft delete.
    FDA compliance requires records not be permanently deleted.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'iam.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """
        Soft delete the record.
        Sets is_deleted=True and records who deleted it.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        """
        Restore a soft-deleted record.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def delete(self, *args, **kwargs):
        """
        Override delete to perform soft delete by default.
        Use hard_delete() for permanent deletion if absolutely necessary.
        """
        self.soft_delete()

    def hard_delete(self, *args, **kwargs):
        """
        Permanently delete the record.
        WARNING: This bypasses soft delete. Use with extreme caution.
        """
        super().delete(*args, **kwargs)


class AuditableModel(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """
    Base model for all auditable entities in the EBR system.

    Includes:
    - UUID primary key for global uniqueness
    - Automatic timestamps (created_at, updated_at)
    - Soft delete functionality
    - Creator/modifier tracking
    - Integrity checksum for tamper detection

    All batch records, steps, and compliance-critical data should
    inherit from this model.
    """
    created_by = models.ForeignKey(
        'iam.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created'
    )
    modified_by = models.ForeignKey(
        'iam.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_modified'
    )

    # Integrity verification
    record_checksum = models.CharField(
        max_length=64,
        editable=False,
        blank=True,
        help_text='SHA-256 checksum of record data for integrity verification'
    )
    checksum_algorithm = models.CharField(
        max_length=20,
        default='sha256',
        editable=False
    )

    # Version for optimistic locking
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True

    def calculate_checksum(self):
        """
        Calculate SHA-256 checksum of record data.
        Override _get_checksum_fields() in subclasses to customize.
        """
        data = self._get_checksum_fields()
        data_str = str(sorted(data.items()))
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _get_checksum_fields(self):
        """
        Get fields to include in checksum calculation.
        Override in subclass to define which fields should be
        included in integrity verification.
        """
        exclude_fields = {
            'record_checksum',
            'checksum_algorithm',
            'updated_at',
            'modified_by',
            'version'
        }
        return {
            f.name: getattr(self, f.name)
            for f in self._meta.fields
            if f.name not in exclude_fields
        }

    def verify_integrity(self):
        """
        Verify record has not been tampered with.
        Returns True if checksum matches, False otherwise.
        """
        return self.record_checksum == self.calculate_checksum()

    def save(self, *args, **kwargs):
        """
        Override save to update checksum and version.
        """
        # Update checksum before saving
        self.record_checksum = self.calculate_checksum()

        # Increment version for optimistic locking
        if self.pk:
            self.version += 1

        super().save(*args, **kwargs)
