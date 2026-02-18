"""
Custom validators for the EBR system.
"""
import re
from decimal import Decimal
from typing import Any, Optional
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


# ============================================================================
# Regex Patterns
# ============================================================================

# Kenya phone number: +254XXXXXXXXX or 07XXXXXXXX
KENYA_PHONE_REGEX = r'^(?:\+254|0)[17]\d{8}$'

# Kenya ID number: 8 digits
KENYA_ID_REGEX = r'^\d{8}$'

# Alphanumeric codes with optional hyphens/underscores
CODE_REGEX = r'^[A-Za-z0-9][A-Za-z0-9_-]*$'

# Batch number format: PREFIX-YYYYMMDD-XXXX
BATCH_NUMBER_REGEX = r'^[A-Z]{2,4}-\d{8}-\d{4,6}$'

# Lot number format: LOT-YYYYMMDD-XXX
LOT_NUMBER_REGEX = r'^LOT-\d{8}-\d{3,6}$'


# ============================================================================
# Regex Validators
# ============================================================================

validate_kenya_phone = RegexValidator(
    regex=KENYA_PHONE_REGEX,
    message=_('Enter a valid Kenya phone number (e.g., +254712345678 or 0712345678).'),
    code='invalid_kenya_phone',
)

validate_kenya_id = RegexValidator(
    regex=KENYA_ID_REGEX,
    message=_('Enter a valid Kenya ID number (8 digits).'),
    code='invalid_kenya_id',
)

validate_code = RegexValidator(
    regex=CODE_REGEX,
    message=_('Code must start with a letter or number and contain only letters, numbers, hyphens, and underscores.'),
    code='invalid_code',
)

validate_batch_number = RegexValidator(
    regex=BATCH_NUMBER_REGEX,
    message=_('Batch number must be in format: PREFIX-YYYYMMDD-XXXX (e.g., MFG-20240101-0001).'),
    code='invalid_batch_number',
)

validate_lot_number = RegexValidator(
    regex=LOT_NUMBER_REGEX,
    message=_('Lot number must be in format: LOT-YYYYMMDD-XXX (e.g., LOT-20240101-001).'),
    code='invalid_lot_number',
)


# ============================================================================
# Custom Validators
# ============================================================================

def validate_positive(value: Any) -> None:
    """Validate that a number is positive."""
    if value is not None and value <= 0:
        raise ValidationError(
            _('Value must be positive.'),
            code='not_positive',
        )


def validate_non_negative(value: Any) -> None:
    """Validate that a number is non-negative."""
    if value is not None and value < 0:
        raise ValidationError(
            _('Value cannot be negative.'),
            code='negative_value',
        )


def validate_percentage(value: Any) -> None:
    """Validate that a value is a valid percentage (0-100)."""
    if value is not None:
        if value < 0 or value > 100:
            raise ValidationError(
                _('Percentage must be between 0 and 100.'),
                code='invalid_percentage',
            )


def validate_decimal_places(value: Decimal, max_places: int = 2) -> None:
    """Validate decimal places don't exceed maximum."""
    if value is not None:
        sign, digits, exponent = value.as_tuple()
        if exponent < 0 and abs(exponent) > max_places:
            raise ValidationError(
                _('Value cannot have more than %(max)s decimal places.'),
                code='too_many_decimal_places',
                params={'max': max_places},
            )


def validate_no_html(value: str) -> None:
    """Validate that a string doesn't contain HTML tags."""
    if value and re.search(r'<[^>]+>', value):
        raise ValidationError(
            _('HTML tags are not allowed.'),
            code='contains_html',
        )


def validate_no_script(value: str) -> None:
    """Validate that a string doesn't contain script tags or JavaScript."""
    if value:
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'on\w+\s*=',  # onclick, onload, etc.
            r'data:text/html',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError(
                    _('Potentially dangerous content detected.'),
                    code='dangerous_content',
                )


def validate_json_schema(value: dict, required_fields: Optional[list] = None) -> None:
    """Validate a JSON dict has required fields."""
    if required_fields and value:
        missing = [f for f in required_fields if f not in value]
        if missing:
            raise ValidationError(
                _('Missing required fields: %(fields)s'),
                code='missing_fields',
                params={'fields': ', '.join(missing)},
            )


def validate_date_range(start_date, end_date) -> None:
    """Validate that start_date is before end_date."""
    if start_date and end_date and start_date > end_date:
        raise ValidationError(
            _('Start date must be before end date.'),
            code='invalid_date_range',
        )


def validate_future_date(value) -> None:
    """Validate that a date is in the future."""
    from django.utils import timezone
    if value and value < timezone.now().date():
        raise ValidationError(
            _('Date must be in the future.'),
            code='date_not_future',
        )


def validate_past_date(value) -> None:
    """Validate that a date is in the past or today."""
    from django.utils import timezone
    if value and value > timezone.now().date():
        raise ValidationError(
            _('Date cannot be in the future.'),
            code='date_in_future',
        )


def validate_file_extension(value, allowed_extensions: list) -> None:
    """Validate file extension is in allowed list."""
    import os
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            _('File type "%(ext)s" is not allowed. Allowed types: %(allowed)s'),
            code='invalid_file_type',
            params={
                'ext': ext,
                'allowed': ', '.join(allowed_extensions),
            },
        )


def validate_file_size(value, max_size_mb: int = 10) -> None:
    """Validate file size is within limit."""
    max_bytes = max_size_mb * 1024 * 1024
    if value.size > max_bytes:
        raise ValidationError(
            _('File size cannot exceed %(max)s MB.'),
            code='file_too_large',
            params={'max': max_size_mb},
        )


class PasswordStrengthValidator:
    """
    Validate password meets strength requirements.
    """

    def __init__(
        self,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
    ):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special

    def validate(self, password: str, user=None) -> None:
        errors = []

        if len(password) < self.min_length:
            errors.append(
                _('Password must be at least %(min)s characters long.') % {'min': self.min_length}
            )

        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append(_('Password must contain at least one uppercase letter.'))

        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append(_('Password must contain at least one lowercase letter.'))

        if self.require_digit and not re.search(r'\d', password):
            errors.append(_('Password must contain at least one digit.'))

        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(_('Password must contain at least one special character.'))

        if errors:
            raise ValidationError(errors)

    def get_help_text(self) -> str:
        requirements = [f'at least {self.min_length} characters']
        if self.require_uppercase:
            requirements.append('one uppercase letter')
        if self.require_lowercase:
            requirements.append('one lowercase letter')
        if self.require_digit:
            requirements.append('one digit')
        if self.require_special:
            requirements.append('one special character')
        return _('Password must contain: %(reqs)s.') % {'reqs': ', '.join(requirements)}


class UniqueForTenantValidator:
    """
    Validate a field is unique within a tenant.
    """

    def __init__(self, model, field_name: str, message: Optional[str] = None):
        self.model = model
        self.field_name = field_name
        self.message = message or _('This value already exists for this tenant.')

    def __call__(self, value, instance=None, tenant_id=None):
        queryset = self.model.objects.filter(
            tenant_id=tenant_id,
            **{self.field_name: value}
        )
        if instance and instance.pk:
            queryset = queryset.exclude(pk=instance.pk)

        if queryset.exists():
            raise ValidationError(self.message, code='unique_for_tenant')
