"""
Role-Based Access Control (RBAC) models for the EBR Platform.

Implements granular permission system with:
- Permissions: Individual access rights
- Roles: Collections of permissions
- User-Role assignments with scope and validity period
"""
import uuid
from django.db import models


class Permission(models.Model):
    """
    Granular permission for RBAC.

    Permissions follow the pattern: module.resource.action
    Examples:
    - batch_records.batch.create
    - batch_records.batch.approve
    - healthcare.patient.view
    - manufacturing.equipment.calibrate
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    code = models.CharField(
        max_length=100,
        unique=True,
        help_text='Permission code (e.g., batch_records.batch.create)'
    )
    name = models.CharField(
        max_length=255,
        help_text='Human-readable permission name'
    )
    description = models.TextField(
        blank=True,
        help_text='Detailed description of what this permission allows'
    )

    # Categorization
    module = models.CharField(
        max_length=50,
        help_text='Module this permission belongs to (core, healthcare, etc.)'
    )
    resource = models.CharField(
        max_length=50,
        help_text='Resource this permission applies to (batch, patient, etc.)'
    )
    action = models.CharField(
        max_length=50,
        help_text='Action type (create, read, update, delete, approve, etc.)'
    )

    # Metadata
    is_system = models.BooleanField(
        default=False,
        help_text='Whether this is a system-level permission'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['module', 'resource', 'action']
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'

    def __str__(self):
        return f"{self.code} - {self.name}"


class Role(models.Model):
    """
    Role with assigned permissions.

    Roles can inherit permissions from a parent role,
    enabling hierarchical permission structures.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Role name (e.g., Batch Operator, QC Manager)'
    )
    code = models.SlugField(
        unique=True,
        help_text='URL-friendly role identifier'
    )
    description = models.TextField(
        blank=True,
        help_text='Description of role responsibilities'
    )

    # Hierarchy
    parent_role = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_roles',
        help_text='Parent role to inherit permissions from'
    )

    # Permissions
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='roles'
    )

    # Metadata
    is_system_role = models.BooleanField(
        default=False,
        help_text='Whether this is a built-in system role'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name

    def get_all_permissions(self):
        """
        Get all permissions including those inherited from parent roles.
        """
        permissions = set(self.permissions.all())

        if self.parent_role:
            permissions.update(self.parent_role.get_all_permissions())

        return permissions

    def has_permission(self, permission_code):
        """Check if role has a specific permission."""
        all_perms = self.get_all_permissions()
        return any(p.code == permission_code for p in all_perms)


class RolePermission(models.Model):
    """
    Through model for Role-Permission relationship.
    Allows tracking when permissions were granted.
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        'iam.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )

    class Meta:
        unique_together = ['role', 'permission']
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'

    def __str__(self):
        return f"{self.role.name} - {self.permission.code}"


class UserRole(models.Model):
    """
    User-Role assignment with optional scope and validity period.

    Supports:
    - Global role assignment (no scope)
    - Scoped assignment (e.g., role only applies to specific department)
    - Time-limited role assignment
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'iam.User',
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_assignments'
    )

    # Scope restriction (optional)
    scope_type = models.CharField(
        max_length=50,
        blank=True,
        help_text='Type of scope restriction (e.g., department, facility, product_line)'
    )
    scope_id = models.UUIDField(
        null=True,
        blank=True,
        help_text='ID of the scoped entity'
    )
    scope_name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Human-readable scope name for display'
    )

    # Validity period
    valid_from = models.DateTimeField(
        auto_now_add=True,
        help_text='When this role assignment becomes effective'
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this role assignment expires (null = no expiration)'
    )

    # Audit fields
    assigned_by = models.ForeignKey(
        'iam.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='role_assignments_made'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(
        blank=True,
        help_text='Reason for role assignment'
    )

    class Meta:
        verbose_name = 'User Role Assignment'
        verbose_name_plural = 'User Role Assignments'
        indexes = [
            models.Index(fields=['user', 'valid_from', 'valid_until']),
        ]

    def __str__(self):
        scope_str = f" ({self.scope_name})" if self.scope_name else ""
        return f"{self.user.email} - {self.role.name}{scope_str}"

    @property
    def is_valid(self):
        """Check if this role assignment is currently valid."""
        from django.utils import timezone
        now = timezone.now()

        if now < self.valid_from:
            return False

        if self.valid_until and now > self.valid_until:
            return False

        return True
