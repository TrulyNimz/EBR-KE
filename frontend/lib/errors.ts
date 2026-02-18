/**
 * Error handling utilities for the EBR frontend.
 */

// ============================================================================
// Error Types
// ============================================================================

export interface APIErrorDetails {
  [field: string]: string[];
}

export interface APIError {
  type: string;
  code: string;
  message: string;
  details?: APIErrorDetails;
  extra?: Record<string, unknown>;
}

export interface APIErrorResponse {
  success: false;
  error: APIError;
  request_id?: string;
}

// ============================================================================
// Custom Error Classes
// ============================================================================

export class EBRError extends Error {
  constructor(
    message: string,
    public code: string = 'EBR_ERROR',
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'EBRError';
  }
}

export class ValidationError extends EBRError {
  constructor(
    message: string,
    public fieldErrors?: APIErrorDetails,
    details?: Record<string, unknown>
  ) {
    super(message, 'VALIDATION_ERROR', details);
    this.name = 'ValidationError';
  }

  /**
   * Get error message for a specific field.
   */
  getFieldError(field: string): string | undefined {
    return this.fieldErrors?.[field]?.[0];
  }

  /**
   * Get all field errors as a flat object.
   */
  getFlatFieldErrors(): Record<string, string> {
    if (!this.fieldErrors) return {};
    return Object.fromEntries(
      Object.entries(this.fieldErrors).map(([key, errors]) => [key, errors[0]])
    );
  }
}

export class AuthenticationError extends EBRError {
  constructor(message: string = 'Authentication required') {
    super(message, 'AUTHENTICATION_ERROR');
    this.name = 'AuthenticationError';
  }
}

export class PermissionError extends EBRError {
  constructor(message: string = 'Permission denied') {
    super(message, 'PERMISSION_ERROR');
    this.name = 'PermissionError';
  }
}

export class NotFoundError extends EBRError {
  constructor(resource: string = 'Resource', id?: string) {
    super(id ? `${resource} with ID ${id} not found` : `${resource} not found`, 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

export class NetworkError extends EBRError {
  constructor(message: string = 'Network error. Please check your connection.') {
    super(message, 'NETWORK_ERROR');
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends EBRError {
  constructor(message: string = 'Request timed out. Please try again.') {
    super(message, 'TIMEOUT_ERROR');
    this.name = 'TimeoutError';
  }
}

export class ConflictError extends EBRError {
  constructor(message: string = 'A conflict occurred. The resource may have been modified.') {
    super(message, 'CONFLICT_ERROR');
    this.name = 'ConflictError';
  }
}

export class WorkflowError extends EBRError {
  constructor(
    message: string,
    public currentState?: string,
    public targetState?: string
  ) {
    super(message, 'WORKFLOW_ERROR', { currentState, targetState });
    this.name = 'WorkflowError';
  }
}

// ============================================================================
// Error Parsing
// ============================================================================

/**
 * Check if an error response matches our API error format.
 */
export function isAPIErrorResponse(data: unknown): data is APIErrorResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'success' in data &&
    data.success === false &&
    'error' in data &&
    typeof (data as APIErrorResponse).error === 'object'
  );
}

/**
 * Parse an API error response into an appropriate error class.
 */
export function parseAPIError(response: APIErrorResponse): EBRError {
  const { error } = response;

  switch (error.type) {
    case 'validation_error':
      return new ValidationError(error.message, error.details);

    case 'authentication_error':
      return new AuthenticationError(error.message);

    case 'permission_error':
      return new PermissionError(error.message);

    case 'not_found_error':
      return new NotFoundError(error.message);

    case 'conflict_error':
      return new ConflictError(error.message);

    case 'workflow_error':
      return new WorkflowError(
        error.message,
        error.extra?.current_state as string,
        error.extra?.target_state as string
      );

    default:
      return new EBRError(error.message, error.code, error.extra);
  }
}

/**
 * Handle fetch errors and convert to appropriate error types.
 */
export function handleFetchError(error: unknown): never {
  // Network error
  if (error instanceof TypeError && error.message.includes('fetch')) {
    throw new NetworkError();
  }

  // Abort/timeout error
  if (error instanceof DOMException && error.name === 'AbortError') {
    throw new TimeoutError();
  }

  // Already an EBR error
  if (error instanceof EBRError) {
    throw error;
  }

  // Generic error
  throw new EBRError(
    error instanceof Error ? error.message : 'An unexpected error occurred',
    'UNKNOWN_ERROR'
  );
}

// ============================================================================
// Error Display Utilities
// ============================================================================

/**
 * Get a user-friendly error message.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof EBRError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  return 'An unexpected error occurred';
}

/**
 * Get field-level validation errors for form display.
 */
export function getFieldErrors(error: unknown): Record<string, string> {
  if (error instanceof ValidationError) {
    return error.getFlatFieldErrors();
  }
  return {};
}

/**
 * Check if error is a specific type.
 */
export function isValidationError(error: unknown): error is ValidationError {
  return error instanceof ValidationError;
}

export function isAuthenticationError(error: unknown): error is AuthenticationError {
  return error instanceof AuthenticationError;
}

export function isPermissionError(error: unknown): error is PermissionError {
  return error instanceof PermissionError;
}

export function isNotFoundError(error: unknown): error is NotFoundError {
  return error instanceof NotFoundError;
}

export function isNetworkError(error: unknown): error is NetworkError {
  return error instanceof NetworkError;
}

// ============================================================================
// HTTP Status Code Mapping
// ============================================================================

export function errorFromStatusCode(status: number, message?: string): EBRError {
  switch (status) {
    case 400:
      return new ValidationError(message || 'Invalid request');
    case 401:
      return new AuthenticationError(message);
    case 403:
      return new PermissionError(message);
    case 404:
      return new NotFoundError(message);
    case 409:
      return new ConflictError(message);
    case 422:
      return new EBRError(message || 'Unprocessable entity', 'BUSINESS_RULE_ERROR');
    case 429:
      return new EBRError(message || 'Too many requests', 'RATE_LIMIT_ERROR');
    case 500:
    case 502:
    case 503:
    case 504:
      return new EBRError(message || 'Server error. Please try again later.', 'SERVER_ERROR');
    default:
      return new EBRError(message || 'An error occurred', 'HTTP_ERROR');
  }
}
