"""
Multi-tenant models for the EBR Platform.

Uses django-tenants for PostgreSQL schema-based isolation.
Each tenant gets their own database schema with isolated data.
"""
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Tenant(TenantMixin):
    """
    Multi-tenant organization model.

    Each tenant represents a separate organization (hospital, factory, farm)
    with isolated data in their own PostgreSQL schema.
    """
    # Basic Information
    name = models.CharField(
        max_length=255,
        help_text='Organization name'
    )
    slug = models.SlugField(
        unique=True,
        help_text='URL-friendly identifier (e.g., acme-hospital)'
    )

    # Industry Type
    INDUSTRY_CHOICES = [
        ('healthcare', 'Healthcare'),
        ('manufacturing', 'Manufacturing'),
        ('agriculture', 'Agriculture'),
    ]
    industry = models.CharField(
        max_length=50,
        choices=INDUSTRY_CHOICES,
        help_text='Primary industry for this tenant'
    )

    # Contact Information
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    # Subscription & Billing
    SUBSCRIPTION_TIERS = [
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    subscription_tier = models.CharField(
        max_length=50,
        choices=SUBSCRIPTION_TIERS,
        default='starter'
    )
    subscription_expires = models.DateTimeField(null=True, blank=True)
    is_trial = models.BooleanField(default=True)

    # Module Activation
    enabled_modules = models.JSONField(
        default=list,
        help_text='List of enabled module codes: ["healthcare", "manufacturing", "agriculture"]'
    )

    # Branding
    logo_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, default='#3B82F6')  # Hex color
    secondary_color = models.CharField(max_length=7, default='#1E40AF')

    # Configuration
    settings = models.JSONField(
        default=dict,
        help_text='Tenant-specific settings and feature flags'
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # django-tenants configuration
    auto_create_schema = True

    class Meta:
        ordering = ['name']
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'

    def __str__(self):
        return f"{self.name} ({self.industry})"

    def has_module(self, module_code):
        """Check if tenant has a specific module enabled."""
        return module_code in self.enabled_modules

    def get_compliance_settings(self):
        """Get tenant's compliance settings with defaults."""
        defaults = {
            'require_digital_signatures': True,
            'require_witness_signatures': False,
            'session_timeout_minutes': 30,
            'password_expiry_days': 90,
            'mfa_required': True,
            'audit_retention_days': 2555,  # 7 years
        }
        return {**defaults, **self.settings.get('compliance', {})}


class Domain(DomainMixin):
    """
    Domain mapping for tenants.

    Supports:
    - Subdomain routing: acme.ebr-platform.com
    - Custom domains: ebr.acme-hospital.com
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='domains'
    )

    class Meta:
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'

    def __str__(self):
        return self.domain


class TenantSettings(models.Model):
    """
    Extended tenant configuration for compliance and operational settings.
    """
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name='extended_settings'
    )

    # Compliance Mode
    COMPLIANCE_MODES = [
        ('fda_21cfr11', 'FDA 21 CFR Part 11'),
        ('gmp', 'Good Manufacturing Practice'),
        ('hipaa', 'HIPAA'),
        ('iso_22000', 'ISO 22000 Food Safety'),
        ('kenya_dpa', 'Kenya Data Protection Act'),
    ]
    compliance_mode = models.CharField(
        max_length=50,
        choices=COMPLIANCE_MODES,
        default='fda_21cfr11',
        help_text='Primary compliance framework'
    )

    # Audit Settings
    audit_retention_days = models.PositiveIntegerField(
        default=2555,  # 7 years
        help_text='Number of days to retain audit logs'
    )
    require_digital_signatures = models.BooleanField(
        default=True,
        help_text='Require digital signatures for approvals'
    )
    require_witness_signatures = models.BooleanField(
        default=False,
        help_text='Require witness counter-signatures'
    )

    # Security Settings
    require_mfa = models.BooleanField(
        default=True,
        help_text='Require multi-factor authentication'
    )
    session_timeout_minutes = models.PositiveIntegerField(
        default=30,
        help_text='Idle session timeout in minutes'
    )
    password_expiry_days = models.PositiveIntegerField(
        default=90,
        help_text='Password expiration period in days'
    )
    max_login_attempts = models.PositiveIntegerField(
        default=5,
        help_text='Maximum failed login attempts before lockout'
    )

    # Workflow Settings
    default_approval_timeout_hours = models.PositiveIntegerField(
        default=72,
        help_text='Default timeout for pending approvals'
    )
    auto_escalation_enabled = models.BooleanField(
        default=True,
        help_text='Enable automatic escalation for overdue approvals'
    )

    # Offline Settings (for mobile)
    allow_offline_mode = models.BooleanField(
        default=True,
        help_text='Allow mobile app to work offline'
    )
    max_offline_days = models.PositiveIntegerField(
        default=7,
        help_text='Maximum days allowed for offline operation'
    )

    # Data Localization
    data_region = models.CharField(
        max_length=50,
        default='ke-nairobi',
        help_text='Data residency region'
    )
    timezone = models.CharField(
        max_length=50,
        default='Africa/Nairobi'
    )

    class Meta:
        verbose_name = 'Tenant Settings'
        verbose_name_plural = 'Tenant Settings'

    def __str__(self):
        return f"Settings for {self.tenant.name}"
