'use client';

import { useForm, Controller, UseFormReturn } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMemo } from 'react';

// JSON Schema to Zod converter
function jsonSchemaToZod(schema: JsonSchema): z.ZodTypeAny {
  if (!schema || typeof schema !== 'object') {
    return z.any();
  }

  switch (schema.type) {
    case 'string':
      let stringSchema = z.string();
      if (schema.minLength) stringSchema = stringSchema.min(schema.minLength);
      if (schema.maxLength) stringSchema = stringSchema.max(schema.maxLength);
      if (schema.pattern) stringSchema = stringSchema.regex(new RegExp(schema.pattern));
      if (schema.enum) return z.enum(schema.enum as [string, ...string[]]);
      if (!schema.required) return stringSchema.optional();
      return stringSchema;

    case 'number':
    case 'integer':
      let numberSchema = schema.type === 'integer' ? z.number().int() : z.number();
      if (schema.minimum !== undefined) numberSchema = numberSchema.min(schema.minimum);
      if (schema.maximum !== undefined) numberSchema = numberSchema.max(schema.maximum);
      if (!schema.required) return numberSchema.optional();
      return numberSchema;

    case 'boolean':
      return schema.required ? z.boolean() : z.boolean().optional();

    case 'array':
      const itemSchema = schema.items ? jsonSchemaToZod(schema.items) : z.any();
      let arraySchema = z.array(itemSchema);
      if (schema.minItems) arraySchema = arraySchema.min(schema.minItems);
      if (schema.maxItems) arraySchema = arraySchema.max(schema.maxItems);
      if (!schema.required) return arraySchema.optional();
      return arraySchema;

    case 'object':
      if (schema.properties) {
        const shape: Record<string, z.ZodTypeAny> = {};
        Object.entries(schema.properties).forEach(([key, propSchema]) => {
          const isRequired = schema.required?.includes(key);
          shape[key] = jsonSchemaToZod({ ...propSchema as JsonSchema, required: isRequired });
        });
        return z.object(shape);
      }
      return z.record(z.any());

    default:
      return z.any();
  }
}

interface JsonSchema {
  type?: string;
  title?: string;
  description?: string;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  enum?: string[];
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  items?: JsonSchema;
  minItems?: number;
  maxItems?: number;
  format?: string;
}

interface DynamicFormProps {
  schema: JsonSchema;
  defaultValues?: Record<string, unknown>;
  onSubmit: (data: Record<string, unknown>) => void;
  onCancel?: () => void;
  submitLabel?: string;
  loading?: boolean;
}

export function DynamicForm({
  schema,
  defaultValues = {},
  onSubmit,
  onCancel,
  submitLabel = 'Submit',
  loading = false,
}: DynamicFormProps) {
  const zodSchema = useMemo(() => jsonSchemaToZod(schema), [schema]);

  const form = useForm({
    resolver: zodResolver(zodSchema as z.ZodType<Record<string, unknown>>),
    defaultValues,
  });

  const handleSubmit = form.handleSubmit(onSubmit);

  if (!schema.properties) {
    return <p className="text-gray-500">No form fields defined</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {Object.entries(schema.properties).map(([key, fieldSchema]) => (
        <DynamicField
          key={key}
          name={key}
          schema={fieldSchema}
          form={form}
          required={schema.required?.includes(key)}
        />
      ))}

      <div className="flex items-center justify-end gap-3 pt-4">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Saving...' : submitLabel}
        </button>
      </div>
    </form>
  );
}

interface DynamicFieldProps {
  name: string;
  schema: JsonSchema;
  form: UseFormReturn<Record<string, unknown>>;
  required?: boolean;
}

function DynamicField({ name, schema, form, required }: DynamicFieldProps) {
  const { control, formState: { errors } } = form;
  const error = errors[name];
  const inputClasses =
    'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent';

  const renderField = () => {
    switch (schema.type) {
      case 'string':
        if (schema.enum) {
          return (
            <Controller
              name={name}
              control={control}
              render={({ field }) => (
                <select {...field} value={field.value as string || ''} className={inputClasses}>
                  <option value="">Select...</option>
                  {schema.enum?.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              )}
            />
          );
        }
        if (schema.format === 'date') {
          return (
            <Controller
              name={name}
              control={control}
              render={({ field }) => (
                <input
                  type="date"
                  {...field}
                  value={field.value as string || ''}
                  className={inputClasses}
                />
              )}
            />
          );
        }
        if (schema.format === 'datetime' || schema.format === 'date-time') {
          return (
            <Controller
              name={name}
              control={control}
              render={({ field }) => (
                <input
                  type="datetime-local"
                  {...field}
                  value={field.value as string || ''}
                  className={inputClasses}
                />
              )}
            />
          );
        }
        if (schema.format === 'textarea' || (schema.maxLength && schema.maxLength > 200)) {
          return (
            <Controller
              name={name}
              control={control}
              render={({ field }) => (
                <textarea
                  {...field}
                  value={field.value as string || ''}
                  rows={4}
                  className={inputClasses}
                />
              )}
            />
          );
        }
        return (
          <Controller
            name={name}
            control={control}
            render={({ field }) => (
              <input
                type="text"
                {...field}
                value={field.value as string || ''}
                className={inputClasses}
              />
            )}
          />
        );

      case 'number':
      case 'integer':
        return (
          <Controller
            name={name}
            control={control}
            render={({ field }) => (
              <input
                type="number"
                {...field}
                value={field.value as number ?? ''}
                onChange={(e) => field.onChange(e.target.valueAsNumber)}
                min={schema.minimum}
                max={schema.maximum}
                step={schema.type === 'integer' ? 1 : 'any'}
                className={inputClasses}
              />
            )}
          />
        );

      case 'boolean':
        return (
          <Controller
            name={name}
            control={control}
            render={({ field }) => (
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={field.value as boolean || false}
                  onChange={(e) => field.onChange(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Yes</span>
              </label>
            )}
          />
        );

      default:
        return (
          <Controller
            name={name}
            control={control}
            render={({ field }) => (
              <input
                type="text"
                {...field}
                value={String(field.value || '')}
                className={inputClasses}
              />
            )}
          />
        );
    }
  };

  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {schema.title || name}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {renderField()}
      {schema.description && (
        <p className="text-xs text-gray-500">{schema.description}</p>
      )}
      {error && (
        <p className="text-xs text-red-500">
          {error.message as string}
        </p>
      )}
    </div>
  );
}
