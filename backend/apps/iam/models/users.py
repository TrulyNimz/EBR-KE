"""
Custom User model for the EBR Platform.

Implements FDA 21 CFR Part 11 compliance features including:
- Unique user identification
- Password policies
- Account lockout
- MFA support
- Digital signature capabilities
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager for User model."""

    def create_user(self, email, employee_id, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('Users must have an email address')
        if not employee_id:
            raise ValueError('Users must have an employee ID')

        email = self.normalize_email(email)
        user = self.model(email=email, employee_id=employee_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, employee_id, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, employee_id, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with FDA 21 CFR Part 11 compliance features.

    Key compliance features:
    - Unique identification via email and employee_id
    - Password expiration tracking
    - Account lockout after failed attempts
    - MFA support (TOTP)
    - Digital signature key management
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Basic Information
    email = models.EmailField(
        unique=True,
        help_text='Primary email address (used for login)'
    )
    employee_id = models.CharField(
        max_length=50,
        unique=True,
        help_text='Unique employee identifier'
    )

    # Profile (stored encrypted at database level in production)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)

    # Status Flags
    is_active = models.BooleanField(
        default=True,
        help_text='Whether the user account is active'
    )
    is_staff = models.BooleanField(
        default=False,
        help_text='Whether user can access admin site'
    )

    # Account Lockout
    is_locked = models.BooleanField(
        default=False,
        help_text='Whether account is locked due to failed logins'
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_reason = models.CharField(max_length=255, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)

    # Password Management
    password_changed_at = models.DateTimeField(null=True, blank=True)
    password_expires_at = models.DateTimeField(null=True, blank=True)
    password_history = models.JSONField(
        default=list,
        help_text='Hashes of previous passwords to prevent reuse'
    )
    must_change_password = models.BooleanField(
        default=False,
        help_text='Force password change on next login'
    )

    # Session & Login Tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_user_agent = models.TextField(blank=True)

    # MFA (Multi-Factor Authentication)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(
        max_length=255,
        blank=True,
        help_text='TOTP secret (encrypted)'
    )
    mfa_backup_codes = models.JSONField(
        default=list,
        help_text='One-time backup codes for MFA recovery'
    )
    mfa_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When MFA was last verified'
    )

    # Digital Signature
    digital_signature_enabled = models.BooleanField(default=False)
    signature_private_key = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted RSA private key for digital signatures'
    )
    signature_public_key = models.BinaryField(
        null=True,
        blank=True,
        help_text='Public key for signature verification'
    )
    signature_certificate = models.TextField(
        blank=True,
        help_text='X.509 certificate for digital signature'
    )
    signature_pin_hash = models.CharField(
        max_length=255,
        blank=True,
        help_text='Hashed PIN for signature authorization'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['employee_id', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_password_expired(self):
        """Check if the user's password has expired."""
        if not self.password_expires_at:
            return False
        return timezone.now() > self.password_expires_at

    def lock_account(self, reason='Too many failed login attempts'):
        """Lock the user account."""
        self.is_locked = True
        self.locked_at = timezone.now()
        self.locked_reason = reason
        self.save(update_fields=['is_locked', 'locked_at', 'locked_reason'])

    def unlock_account(self):
        """Unlock the user account."""
        self.is_locked = False
        self.locked_at = None
        self.locked_reason = ''
        self.failed_login_attempts = 0
        self.save(update_fields=[
            'is_locked', 'locked_at', 'locked_reason', 'failed_login_attempts'
        ])

    def record_failed_login(self, max_attempts=5):
        """Record a failed login attempt and lock if threshold exceeded."""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()

        if self.failed_login_attempts >= max_attempts:
            self.lock_account()
        else:
            self.save(update_fields=['failed_login_attempts', 'last_failed_login'])

    def record_successful_login(self, ip_address=None, user_agent=None):
        """Record a successful login and reset failed attempts."""
        self.failed_login_attempts = 0
        self.last_login = timezone.now()
        self.last_login_ip = ip_address
        self.last_login_user_agent = user_agent or ''
        self.save(update_fields=[
            'failed_login_attempts', 'last_login', 'last_login_ip', 'last_login_user_agent'
        ])

    def get_all_permissions_set(self):
        """Get all permissions from all assigned roles."""
        from apps.iam.models import UserRole
        permissions = set()
        user_roles = UserRole.objects.filter(
            user=self,
            valid_from__lte=timezone.now()
        ).filter(
            models.Q(valid_until__isnull=True) |
            models.Q(valid_until__gt=timezone.now())
        ).select_related('role')

        for user_role in user_roles:
            role_perms = user_role.role.get_all_permissions()
            permissions.update(p.code for p in role_perms)

        return permissions
