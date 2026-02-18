"""
Custom exception handling for the EBR Platform API.
"""
from typing import Any, Dict, Optional
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.db import IntegrityError as DjangoIntegrityError
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Base Exceptions
# ============================================================================

class EBRException(Exception):
    """Base exception for EBR Platform."""
    default_message = 'An error occurred'
    default_code = 'EBR_ERROR'

    def __init__(self, message=None, code=None, details=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details
        super().__init__(self.message)


class EBRAPIException(APIException):
    """Base API exception for EBR system."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'An error occurred.'
    default_code = 'error'
    error_type = 'general_error'

    def __init__(
        self,
        detail: Optional[str] = None,
        code: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(detail=detail, code=code)
        self.extra = extra or {}


# ============================================================================
# Specific Exceptions
# ============================================================================

class ValidationError(EBRException):
    """Raised when validation fails."""
    default_message = 'Validation failed'
    default_code = 'VALIDATION_ERROR'


class IntegrityError(EBRException):
    """Raised when data integrity check fails."""
    default_message = 'Data integrity verification failed'
    default_code = 'INTEGRITY_ERROR'


class WorkflowError(EBRException):
    """Raised when workflow transition is invalid."""
    default_message = 'Invalid workflow transition'
    default_code = 'WORKFLOW_ERROR'


class SignatureError(EBRException):
    """Raised when digital signature operation fails."""
    default_message = 'Digital signature operation failed'
    default_code = 'SIGNATURE_ERROR'


class PermissionError(EBRException):
    """Raised when permission is denied."""
    default_message = 'Permission denied'
    default_code = 'PERMISSION_ERROR'


class NotFoundError(EBRException):
    """Raised when a resource is not found."""
    default_message = 'Resource not found'
    default_code = 'NOT_FOUND'


class ConflictError(EBRException):
    """Raised when there is a conflict (e.g., duplicate)."""
    default_message = 'Resource conflict'
    default_code = 'CONFLICT_ERROR'


class SyncError(EBRException):
    """Raised when sync fails."""
    default_message = 'Synchronization failed'
    default_code = 'SYNC_ERROR'


class BusinessRuleError(EBRException):
    """Raised when a business rule is violated."""
    default_message = 'Business rule violation'
    default_code = 'BUSINESS_RULE_ERROR'


# ============================================================================
# API Exception Classes
# ============================================================================

class ValidationAPIException(EBRAPIException):
    """Validation error API exception."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Validation failed.'
    default_code = 'validation_error'
    error_type = 'validation_error'


class AuthenticationAPIException(EBRAPIException):
    """Authentication error API exception."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication required.'
    default_code = 'authentication_required'
    error_type = 'authentication_error'


class PermissionDeniedAPIException(EBRAPIException):
    """Permission denied API exception."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to perform this action.'
    default_code = 'permission_denied'
    error_type = 'permission_error'


class NotFoundAPIException(EBRAPIException):
    """Resource not found API exception."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'The requested resource was not found.'
    default_code = 'not_found'
    error_type = 'not_found_error'


class ConflictAPIException(EBRAPIException):
    """Conflict API exception."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'A conflict occurred with the current state of the resource.'
    default_code = 'conflict'
    error_type = 'conflict_error'


class WorkflowAPIException(EBRAPIException):
    """Workflow state transition API exception."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid workflow transition.'
    default_code = 'workflow_error'
    error_type = 'workflow_error'


class SignatureAPIException(EBRAPIException):
    """Digital signature API exception."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Signature validation failed.'
    default_code = 'signature_error'
    error_type = 'signature_error'


class SyncAPIException(EBRAPIException):
    """Sync conflict API exception."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Sync conflict detected.'
    default_code = 'sync_error'
    error_type = 'sync_error'


class RateLimitAPIException(EBRAPIException):
    """Rate limit exceeded API exception."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Too many requests. Please try again later.'
    default_code = 'rate_limit_exceeded'
    error_type = 'rate_limit_error'


class ServiceUnavailableAPIException(EBRAPIException):
    """External service unavailable API exception."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable. Please try again later.'
    default_code = 'service_unavailable'
    error_type = 'service_error'


class BusinessRuleAPIException(EBRAPIException):
    """Business rule violation API exception."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Business rule violation.'
    default_code = 'business_rule_error'
    error_type = 'business_error'


# ============================================================================
# Custom Exception Handler
# ============================================================================

def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF.

    Provides consistent error response format:
    {
        "success": false,
        "error": {
            "type": "validation_error",
            "code": "VALIDATION_ERROR",
            "message": "Human-readable message",
            "details": {...},  # Optional field-level errors
            "extra": {...}     # Optional additional context
        },
        "request_id": "..."    # If available
    }
    """
    # Get the request ID if available
    request = context.get('request')
    request_id = getattr(request, 'request_id', None) if request else None

    # Handle Django ValidationError
    if isinstance(exc, DjangoValidationError):
        exc = ValidationAPIException(
            detail=str(exc.message) if hasattr(exc, 'message') else str(exc),
            extra={'errors': exc.message_dict if hasattr(exc, 'message_dict') else None}
        )

    # Handle 404
    if isinstance(exc, Http404):
        exc = NotFoundAPIException(detail=str(exc))

    # Handle Django IntegrityError
    if isinstance(exc, DjangoIntegrityError):
        logger.error(f"Database integrity error: {exc}")
        exc = ConflictAPIException(
            detail='A database constraint was violated. This may be a duplicate entry.',
            extra={'original_error': str(exc)} if request and hasattr(request, 'user') and request.user.is_staff else {}
        )

    # Handle EBR exceptions
    if isinstance(exc, EBRException):
        exc = EBRAPIException(
            detail=exc.message,
            code=exc.code,
            extra={'details': exc.details} if exc.details else {}
        )

    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Build consistent error response
        error_response = {
            'success': False,
            'error': {
                'type': getattr(exc, 'error_type', 'api_error'),
                'code': getattr(exc, 'default_code', exc.__class__.__name__.upper()),
                'message': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
            }
        }

        # Add field-level validation errors
        if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
            error_response['error']['details'] = exc.detail
            error_response['error']['message'] = 'Validation failed. Check details for specific errors.'

        # Add extra context for EBR exceptions
        if hasattr(exc, 'extra') and exc.extra:
            error_response['error']['extra'] = exc.extra

        # Add request ID
        if request_id:
            error_response['request_id'] = request_id

        response.data = error_response

    else:
        # Handle unexpected exceptions
        logger.exception(f"Unhandled exception: {exc}")

        error_response = {
            'success': False,
            'error': {
                'type': 'server_error',
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'An unexpected error occurred. Please try again later.',
            }
        }

        if request_id:
            error_response['request_id'] = request_id

        response = Response(
            error_response,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response


# ============================================================================
# Helper Functions
# ============================================================================

def raise_validation_error(message: str, field: Optional[str] = None, **extra):
    """Convenience function to raise validation errors."""
    if field:
        raise ValidationAPIException(detail={field: [message]}, extra=extra)
    raise ValidationAPIException(detail=message, extra=extra)


def raise_not_found(resource: str = 'Resource', id: Optional[str] = None):
    """Convenience function to raise not found errors."""
    message = f'{resource} not found'
    if id:
        message = f'{resource} with ID {id} not found'
    raise NotFoundAPIException(detail=message, extra={'resource': resource, 'id': id})


def raise_permission_denied(action: str = 'perform this action', resource: Optional[str] = None):
    """Convenience function to raise permission denied errors."""
    message = f'You do not have permission to {action}'
    if resource:
        message = f'{message} on {resource}'
    raise PermissionDeniedAPIException(detail=message)


def raise_workflow_error(message: str, current_state: Optional[str] = None, target_state: Optional[str] = None):
    """Convenience function to raise workflow errors."""
    extra = {}
    if current_state:
        extra['current_state'] = current_state
    if target_state:
        extra['target_state'] = target_state
    raise WorkflowAPIException(detail=message, extra=extra)


def raise_business_rule_error(message: str, rule: Optional[str] = None):
    """Convenience function to raise business rule errors."""
    extra = {'rule': rule} if rule else {}
    raise BusinessRuleAPIException(detail=message, extra=extra)


def raise_conflict_error(message: str, resource: Optional[str] = None):
    """Convenience function to raise conflict errors."""
    extra = {'resource': resource} if resource else {}
    raise ConflictAPIException(detail=message, extra=extra)
