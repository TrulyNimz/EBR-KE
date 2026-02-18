/**
 * Validation utilities and Zod schemas for the EBR frontend.
 */
import * as z from 'zod';

// ============================================================================
// Common Validation Patterns
// ============================================================================

/**
 * Kenya phone number regex: +254XXXXXXXXX or 07XXXXXXXX or 01XXXXXXXX
 */
export const KENYA_PHONE_REGEX = /^(?:\+254|0)[17]\d{8}$/;

/**
 * Kenya ID number regex: 8 digits
 */
export const KENYA_ID_REGEX = /^\d{8}$/;

/**
 * Alphanumeric code with optional hyphens/underscores
 */
export const CODE_REGEX = /^[A-Za-z0-9][A-Za-z0-9_-]*$/;

/**
 * Batch number format: PREFIX-YYYYMMDD-XXXX
 */
export const BATCH_NUMBER_REGEX = /^[A-Z]{2,4}-\d{8}-\d{4,6}$/;

/**
 * Strong password: min 8 chars, uppercase, lowercase, number, special char
 */
export const STRONG_PASSWORD_REGEX =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>])[A-Za-z\d!@#$%^&*(),.?":{}|<>]{8,}$/;

// ============================================================================
// Zod Schema Helpers
// ============================================================================

/**
 * UUID validation
 */
export const uuidSchema = z.string().uuid('Invalid ID format');

/**
 * Non-empty string that's trimmed
 */
export const requiredString = (fieldName: string = 'Field') =>
  z
    .string({ required_error: `${fieldName} is required` })
    .min(1, `${fieldName} is required`)
    .transform((val) => val.trim());

/**
 * Optional string that's trimmed
 */
export const optionalString = z
  .string()
  .optional()
  .transform((val) => val?.trim() || undefined);

/**
 * Kenya phone number
 */
export const kenyaPhoneSchema = z
  .string()
  .regex(KENYA_PHONE_REGEX, 'Enter a valid Kenya phone number (e.g., +254712345678 or 0712345678)');

/**
 * Kenya ID number
 */
export const kenyaIdSchema = z
  .string()
  .regex(KENYA_ID_REGEX, 'Enter a valid Kenya ID number (8 digits)');

/**
 * Email validation
 */
export const emailSchema = z
  .string()
  .email('Enter a valid email address')
  .toLowerCase()
  .transform((val) => val.trim());

/**
 * Strong password
 */
export const strongPasswordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
  .regex(/\d/, 'Password must contain at least one number')
  .regex(/[!@#$%^&*(),.?":{}|<>]/, 'Password must contain at least one special character');

/**
 * Code/identifier
 */
export const codeSchema = z
  .string()
  .regex(
    CODE_REGEX,
    'Code must start with a letter or number and contain only letters, numbers, hyphens, and underscores'
  )
  .transform((val) => val.trim().toUpperCase());

/**
 * Positive number
 */
export const positiveNumber = z
  .number({ required_error: 'Value is required', invalid_type_error: 'Must be a number' })
  .positive('Value must be positive');

/**
 * Non-negative number
 */
export const nonNegativeNumber = z
  .number({ required_error: 'Value is required', invalid_type_error: 'Must be a number' })
  .nonnegative('Value cannot be negative');

/**
 * Percentage (0-100)
 */
export const percentageSchema = z
  .number({ invalid_type_error: 'Must be a number' })
  .min(0, 'Percentage must be at least 0')
  .max(100, 'Percentage cannot exceed 100');

/**
 * Date string (ISO format)
 */
export const dateStringSchema = z
  .string()
  .refine((val) => !isNaN(Date.parse(val)), 'Invalid date format');

/**
 * Future date
 */
export const futureDateSchema = z.string().refine((val) => {
  const date = new Date(val);
  return !isNaN(date.getTime()) && date > new Date();
}, 'Date must be in the future');

/**
 * Past date (or today)
 */
export const pastDateSchema = z.string().refine((val) => {
  const date = new Date(val);
  const today = new Date();
  today.setHours(23, 59, 59, 999);
  return !isNaN(date.getTime()) && date <= today;
}, 'Date cannot be in the future');

// ============================================================================
// Form Schema Builders
// ============================================================================

/**
 * Create a date range schema with validation.
 */
export function dateRangeSchema(startFieldName: string, endFieldName: string) {
  return z
    .object({
      [startFieldName]: dateStringSchema.optional(),
      [endFieldName]: dateStringSchema.optional(),
    })
    .refine(
      (data) => {
        const start = data[startFieldName];
        const end = data[endFieldName];
        if (start && end) {
          return new Date(start) <= new Date(end);
        }
        return true;
      },
      {
        message: `${endFieldName} must be after ${startFieldName}`,
        path: [endFieldName],
      }
    );
}

/**
 * Create a file validation schema.
 */
export function fileSchema(options: {
  maxSizeMB?: number;
  allowedTypes?: string[];
  required?: boolean;
}) {
  const { maxSizeMB = 10, allowedTypes, required = false } = options;
  const maxBytes = maxSizeMB * 1024 * 1024;

  let schema = z.instanceof(File);

  if (maxSizeMB) {
    schema = schema.refine(
      (file) => file.size <= maxBytes,
      `File size must be less than ${maxSizeMB}MB`
    );
  }

  if (allowedTypes?.length) {
    schema = schema.refine(
      (file) => allowedTypes.includes(file.type),
      `File type must be one of: ${allowedTypes.join(', ')}`
    );
  }

  return required ? schema : schema.optional();
}

// ============================================================================
// Validation Helper Functions
// ============================================================================

/**
 * Validate a value against a Zod schema and return errors.
 */
export function validate<T>(
  schema: z.ZodSchema<T>,
  value: unknown
): { success: true; data: T } | { success: false; errors: Record<string, string> } {
  const result = schema.safeParse(value);

  if (result.success) {
    return { success: true, data: result.data };
  }

  const errors: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const path = issue.path.join('.');
    if (!errors[path]) {
      errors[path] = issue.message;
    }
  }

  return { success: false, errors };
}

/**
 * Sanitize HTML from a string.
 */
export function sanitizeHtml(value: string): string {
  return value
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Check if a string contains potentially dangerous content.
 */
export function containsDangerousContent(value: string): boolean {
  const dangerousPatterns = [
    /<script/i,
    /javascript:/i,
    /on\w+\s*=/i,
    /data:text\/html/i,
  ];

  return dangerousPatterns.some((pattern) => pattern.test(value));
}

/**
 * Format validation errors from API response for react-hook-form.
 */
export function formatAPIErrors(errors: Record<string, string[]>): Record<string, { message: string }> {
  return Object.fromEntries(
    Object.entries(errors).map(([field, messages]) => [field, { message: messages[0] }])
  );
}

// ============================================================================
// Common Form Schemas
// ============================================================================

/**
 * Login form schema
 */
export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required'),
  remember: z.boolean().optional(),
});

export type LoginFormData = z.infer<typeof loginSchema>;

/**
 * Registration form schema
 */
export const registrationSchema = z
  .object({
    firstName: requiredString('First name'),
    lastName: requiredString('Last name'),
    email: emailSchema,
    phone: kenyaPhoneSchema.optional(),
    password: strongPasswordSchema,
    confirmPassword: z.string(),
    termsAccepted: z.literal(true, {
      errorMap: () => ({ message: 'You must accept the terms and conditions' }),
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export type RegistrationFormData = z.infer<typeof registrationSchema>;

/**
 * Password change schema
 */
export const passwordChangeSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: strongPasswordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })
  .refine((data) => data.currentPassword !== data.newPassword, {
    message: 'New password must be different from current password',
    path: ['newPassword'],
  });

export type PasswordChangeFormData = z.infer<typeof passwordChangeSchema>;

/**
 * Profile update schema
 */
export const profileUpdateSchema = z.object({
  firstName: requiredString('First name'),
  lastName: requiredString('Last name'),
  phone: kenyaPhoneSchema.optional(),
  department: optionalString,
  title: optionalString,
});

export type ProfileUpdateFormData = z.infer<typeof profileUpdateSchema>;
