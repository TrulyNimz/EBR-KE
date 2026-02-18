"""
Serializer mixins and utilities for consistent validation.
"""
from typing import Any, Dict, List, Optional
from rest_framework import serializers
from django.utils import timezone


class TenantSerializerMixin:
    """
    Mixin to automatically handle tenant_id in serializers.
    """

    def get_tenant_id(self) -> str:
        """Get tenant_id from request context."""
        request = self.context.get('request')
        if request:
            return getattr(request, 'tenant_id', '')
        return ''

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Add tenant_id to validated data."""
        attrs = super().validate(attrs)
        if hasattr(self.Meta.model, 'tenant_id'):
            attrs['tenant_id'] = self.get_tenant_id()
        return attrs


class AuditSerializerMixin:
    """
    Mixin to automatically handle created_by and modified_by fields.
    """

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Add audit fields to validated data."""
        attrs = super().validate(attrs)
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            model = self.Meta.model
            if self.instance is None:
                # Creating
                if hasattr(model, 'created_by'):
                    attrs['created_by'] = request.user
            # Updating or creating
            if hasattr(model, 'modified_by'):
                attrs['modified_by'] = request.user

        return attrs


class ReadOnlyFieldsMixin:
    """
    Mixin to ensure certain fields are never writable.
    """

    read_only_always_fields: List[str] = [
        'id',
        'created_at',
        'updated_at',
        'created_by',
        'modified_by',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.read_only_always_fields:
            if field_name in self.fields:
                self.fields[field_name].read_only = True


class DateRangeValidationMixin:
    """
    Mixin to validate date ranges in serializers.
    """

    date_range_fields: List[tuple] = []  # List of (start_field, end_field) tuples

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate date ranges."""
        attrs = super().validate(attrs)

        for start_field, end_field in self.date_range_fields:
            start = attrs.get(start_field) or (self.instance and getattr(self.instance, start_field, None))
            end = attrs.get(end_field) or (self.instance and getattr(self.instance, end_field, None))

            if start and end and start > end:
                raise serializers.ValidationError({
                    end_field: f'{end_field} must be after {start_field}.'
                })

        return attrs


class UniqueTogetherValidationMixin:
    """
    Mixin for custom unique together validation with tenant awareness.
    """

    unique_together_fields: List[tuple] = []  # List of field tuples

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique together constraints."""
        attrs = super().validate(attrs)

        for field_combo in self.unique_together_fields:
            filter_kwargs = {}
            for field in field_combo:
                value = attrs.get(field)
                if value is None and self.instance:
                    value = getattr(self.instance, field, None)
                if value is not None:
                    filter_kwargs[field] = value

            # Add tenant_id if model has it
            if hasattr(self.Meta.model, 'tenant_id'):
                filter_kwargs['tenant_id'] = self.get_tenant_id() if hasattr(self, 'get_tenant_id') else ''

            if len(filter_kwargs) == len(field_combo) + (1 if 'tenant_id' in filter_kwargs else 0):
                queryset = self.Meta.model.objects.filter(**filter_kwargs)
                if self.instance:
                    queryset = queryset.exclude(pk=self.instance.pk)
                if queryset.exists():
                    raise serializers.ValidationError(
                        f"This combination of {', '.join(field_combo)} already exists."
                    )

        return attrs


class StatusTransitionMixin:
    """
    Mixin for validating status transitions.
    """

    status_field: str = 'status'
    allowed_transitions: Dict[str, List[str]] = {}

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate status transitions."""
        attrs = super().validate(attrs)

        new_status = attrs.get(self.status_field)
        if new_status and self.instance:
            current_status = getattr(self.instance, self.status_field)
            if current_status != new_status:
                allowed = self.allowed_transitions.get(current_status, [])
                if new_status not in allowed:
                    raise serializers.ValidationError({
                        self.status_field: f"Cannot transition from '{current_status}' to '{new_status}'. "
                                          f"Allowed transitions: {', '.join(allowed) or 'none'}"
                    })

        return attrs


class SanitizationMixin:
    """
    Mixin to sanitize text fields.
    """

    sanitize_fields: List[str] = []
    strip_fields: List[str] = []

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize text fields."""
        import re
        import html

        attrs = super().validate(attrs)

        for field in self.sanitize_fields:
            if field in attrs and attrs[field]:
                # Escape HTML entities
                attrs[field] = html.escape(str(attrs[field]))
                # Remove potential script injections
                attrs[field] = re.sub(r'<script[^>]*>.*?</script>', '', attrs[field], flags=re.IGNORECASE | re.DOTALL)

        for field in self.strip_fields:
            if field in attrs and isinstance(attrs[field], str):
                attrs[field] = attrs[field].strip()

        return attrs


class NestedWriteMixin:
    """
    Mixin to handle nested writable serializers.
    """

    nested_write_fields: Dict[str, str] = {}  # {field_name: related_serializer_class_name}

    def create(self, validated_data: Dict[str, Any]) -> Any:
        """Handle nested creates."""
        nested_data = {}
        for field_name in self.nested_write_fields:
            if field_name in validated_data:
                nested_data[field_name] = validated_data.pop(field_name)

        instance = super().create(validated_data)

        # Create nested objects
        for field_name, items in nested_data.items():
            if items:
                related_field = getattr(instance, field_name)
                for item_data in items:
                    related_field.create(**item_data)

        return instance

    def update(self, instance: Any, validated_data: Dict[str, Any]) -> Any:
        """Handle nested updates."""
        nested_data = {}
        for field_name in self.nested_write_fields:
            if field_name in validated_data:
                nested_data[field_name] = validated_data.pop(field_name)

        instance = super().update(instance, validated_data)

        # Update nested objects (replace strategy)
        for field_name, items in nested_data.items():
            if items is not None:
                related_field = getattr(instance, field_name)
                related_field.all().delete()
                for item_data in items:
                    related_field.create(**item_data)

        return instance


class ValidatedModelSerializer(
    TenantSerializerMixin,
    AuditSerializerMixin,
    ReadOnlyFieldsMixin,
    SanitizationMixin,
    serializers.ModelSerializer
):
    """
    Base serializer with common validation and handling.
    """

    strip_fields = ['name', 'code', 'title', 'description']

    def to_representation(self, instance):
        """Enhance representation with computed fields."""
        data = super().to_representation(instance)

        # Add commonly needed computed fields
        if hasattr(instance, 'created_at'):
            data['created_at_display'] = instance.created_at.strftime('%Y-%m-%d %H:%M:%S') if instance.created_at else None

        return data
