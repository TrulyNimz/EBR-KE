'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { X, Save, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { executeStep } from '@/lib/api/batch-records';
import type { BatchStep } from '@/types/batch-records';

interface StepExecutionFormProps {
  batchId: string;
  step: BatchStep;
  onClose: () => void;
  onComplete: (requiresSignature: boolean) => void;
}

export function StepExecutionForm({
  batchId,
  step,
  onClose,
  onComplete,
}: StepExecutionFormProps) {
  const [formData, setFormData] = useState<Record<string, unknown>>(step.data || {});
  const [deviationNotes, setDeviationNotes] = useState(step.deviation_notes || '');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const executeMutation = useMutation({
    mutationFn: () =>
      executeStep(batchId, step.id, { data: formData, deviation_notes: deviationNotes }),
    onSuccess: () => {
      onComplete(step.requires_signature);
    },
    onError: (error: Error & { response?: { data?: { error?: string } } }) => {
      setErrors({
        _form: error.response?.data?.error || 'Failed to save step data',
      });
    },
  });

  const handleFieldChange = (fieldKey: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [fieldKey]: value }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[fieldKey];
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeMutation.mutate();
  };

  // Render form fields based on the step's form schema
  const renderFormFields = () => {
    const schema = step.form_schema;
    if (!schema || typeof schema !== 'object') {
      return (
        <p className="text-gray-500">No form fields configured for this step.</p>
      );
    }

    const properties = (schema as { properties?: Record<string, unknown> }).properties;
    if (!properties) return null;

    return Object.entries(properties).map(([key, fieldSchema]) => {
      const field = fieldSchema as {
        type?: string;
        title?: string;
        description?: string;
        enum?: string[];
        minimum?: number;
        maximum?: number;
      };

      return (
        <div key={key} className="space-y-1">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            {field.title || key}
          </label>
          {renderField(key, field, formData[key], handleFieldChange)}
          {field.description && (
            <p className="text-xs text-gray-500">{field.description}</p>
          )}
          {errors[key] && (
            <p className="text-xs text-red-500">{errors[key]}</p>
          )}
        </div>
      );
    });
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/50"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {step.name}
              </h2>
              <p className="text-sm text-gray-500">{step.description}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
              {errors._form && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg">
                  <AlertCircle className="w-5 h-5" />
                  <span>{errors._form}</span>
                </div>
              )}

              {renderFormFields()}

              {/* Deviation Notes */}
              <div className="space-y-1">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Notes / Deviation Notes (Optional)
                </label>
                <textarea
                  value={deviationNotes}
                  onChange={(e) => setDeviationNotes(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Add any notes or deviations observed..."
                />
              </div>

              {step.requires_signature && (
                <div className="flex items-center gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400 rounded-lg">
                  <AlertCircle className="w-5 h-5" />
                  <span>
                    This step requires a digital signature: &quot;{step.signature_meaning}&quot;
                  </span>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" loading={executeMutation.isPending}>
                <Save className="w-4 h-4 mr-2" />
                {step.requires_signature ? 'Save & Sign' : 'Save'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function renderField(
  key: string,
  schema: {
    type?: string;
    enum?: string[];
    minimum?: number;
    maximum?: number;
  },
  value: unknown,
  onChange: (key: string, value: unknown) => void
) {
  const baseInputClasses =
    'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent';

  switch (schema.type) {
    case 'string':
      if (schema.enum) {
        return (
          <select
            value={(value as string) || ''}
            onChange={(e) => onChange(key, e.target.value)}
            className={baseInputClasses}
          >
            <option value="">Select...</option>
            {schema.enum.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        );
      }
      return (
        <input
          type="text"
          value={(value as string) || ''}
          onChange={(e) => onChange(key, e.target.value)}
          className={baseInputClasses}
        />
      );

    case 'number':
    case 'integer':
      return (
        <input
          type="number"
          value={(value as number) ?? ''}
          onChange={(e) => onChange(key, e.target.valueAsNumber)}
          min={schema.minimum}
          max={schema.maximum}
          className={baseInputClasses}
        />
      );

    case 'boolean':
      return (
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={(value as boolean) || false}
            onChange={(e) => onChange(key, e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">Yes</span>
        </label>
      );

    default:
      return (
        <input
          type="text"
          value={String(value || '')}
          onChange={(e) => onChange(key, e.target.value)}
          className={baseInputClasses}
        />
      );
  }
}
