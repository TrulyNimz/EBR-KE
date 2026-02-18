"""
Django Admin configuration for Tenant management.
"""
from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from .models import Tenant, Domain, TenantSettings


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1


class TenantSettingsInline(admin.StackedInline):
    model = TenantSettings
    can_delete = False


@admin.register(Tenant)
class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = [
        'name',
        'slug',
        'industry',
        'subscription_tier',
        'is_active',
        'created_at'
    ]
    list_filter = ['industry', 'subscription_tier', 'is_active', 'is_trial']
    search_fields = ['name', 'slug', 'contact_email']
    readonly_fields = ['schema_name', 'created_at', 'updated_at']
    inlines = [DomainInline, TenantSettingsInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'industry', 'schema_name')
        }),
        ('Contact', {
            'fields': ('contact_name', 'contact_email', 'contact_phone', 'address')
        }),
        ('Subscription', {
            'fields': ('subscription_tier', 'subscription_expires', 'is_trial')
        }),
        ('Modules & Settings', {
            'fields': ('enabled_modules', 'settings')
        }),
        ('Branding', {
            'fields': ('logo_url', 'primary_color', 'secondary_color'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__name']
