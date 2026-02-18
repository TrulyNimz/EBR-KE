'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { createBatch } from '@/lib/api/batch-records';
import { apiClient } from '@/lib/api/client';
import type { BatchTemplate, CreateBatchRequest } from '@/types/batch-records';

export default function NewBatchPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<Partial<CreateBatchRequest>>({
    planned_quantity: 0,
    unit_of_measure: 'kg',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Fetch available templates
  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['batch-templates'],
    queryFn: async () => {
      const response = await apiClient.get<{ results: BatchTemplate[] }>(
        '/api/v1/batch-records/templates/'
      );
      return response.data.results;
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateBatchRequest) => createBatch(data),
    onSuccess: (batch) => {
      router.push(`/batch-records/${batch.id}`);
    },
    onError: (error: Error & { response?: { data?: Record<string, string[]> } }) => {
      const responseErrors = error.response?.data;
      if (responseErrors) {
        const formattedErrors: Record<string, string> = {};
        Object.entries(responseErrors).forEach(([key, messages]) => {
          formattedErrors[key] = Array.isArray(messages) ? messages[0] : String(messages);
        });
        setErrors(formattedErrors);
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    // Validate required fields
    const newErrors: Record<string, string> = {};
    if (!formData.template_id) newErrors.template_id = 'Template is required';
    if (!formData.product_name) newErrors.product_name = 'Product name is required';
    if (!formData.product_code) newErrors.product_code = 'Product code is required';
    if (!formData.planned_quantity || formData.planned_quantity <= 0) {
      newErrors.planned_quantity = 'Quantity must be greater than 0';
    }
    if (!formData.planned_start) newErrors.planned_start = 'Planned start is required';
    if (!formData.planned_end) newErrors.planned_end = 'Planned end is required';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    createMutation.mutate(formData as CreateBatchRequest);
  };

  const handleChange = (
    field: keyof CreateBatchRequest,
    value: string | number
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const inputClasses =
    'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent';
  const labelClasses = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1';
  const errorClasses = 'text-xs text-red-500 mt-1';

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => router.back()}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Create New Batch
        </h1>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Batch Information
          </h2>

          <div className="space-y-4">
            {/* Template */}
            <div>
              <label className={labelClasses}>Batch Template *</label>
              <select
                value={formData.template_id || ''}
                onChange={(e) => handleChange('template_id', e.target.value)}
                className={inputClasses}
                disabled={templatesLoading}
              >
                <option value="">Select a template...</option>
                {templates?.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name} (v{template.version})
                  </option>
                ))}
              </select>
              {errors.template_id && (
                <p className={errorClasses}>{errors.template_id}</p>
              )}
            </div>

            {/* Product Name */}
            <div>
              <label className={labelClasses}>Product Name *</label>
              <input
                type="text"
                value={formData.product_name || ''}
                onChange={(e) => handleChange('product_name', e.target.value)}
                className={inputClasses}
                placeholder="Enter product name"
              />
              {errors.product_name && (
                <p className={errorClasses}>{errors.product_name}</p>
              )}
            </div>

            {/* Product Code */}
            <div>
              <label className={labelClasses}>Product Code *</label>
              <input
                type="text"
                value={formData.product_code || ''}
                onChange={(e) => handleChange('product_code', e.target.value)}
                className={inputClasses}
                placeholder="e.g., PRD-001"
              />
              {errors.product_code && (
                <p className={errorClasses}>{errors.product_code}</p>
              )}
            </div>

            {/* Quantity Row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClasses}>Planned Quantity *</label>
                <input
                  type="number"
                  value={formData.planned_quantity || ''}
                  onChange={(e) =>
                    handleChange('planned_quantity', e.target.valueAsNumber)
                  }
                  className={inputClasses}
                  min="0"
                  step="0.01"
                />
                {errors.planned_quantity && (
                  <p className={errorClasses}>{errors.planned_quantity}</p>
                )}
              </div>
              <div>
                <label className={labelClasses}>Unit of Measure *</label>
                <select
                  value={formData.unit_of_measure || 'kg'}
                  onChange={(e) => handleChange('unit_of_measure', e.target.value)}
                  className={inputClasses}
                >
                  <option value="kg">Kilograms (kg)</option>
                  <option value="g">Grams (g)</option>
                  <option value="L">Liters (L)</option>
                  <option value="mL">Milliliters (mL)</option>
                  <option value="units">Units</option>
                  <option value="tablets">Tablets</option>
                  <option value="capsules">Capsules</option>
                </select>
              </div>
            </div>

            {/* Date Row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClasses}>Planned Start *</label>
                <input
                  type="datetime-local"
                  value={formData.planned_start || ''}
                  onChange={(e) => handleChange('planned_start', e.target.value)}
                  className={inputClasses}
                />
                {errors.planned_start && (
                  <p className={errorClasses}>{errors.planned_start}</p>
                )}
              </div>
              <div>
                <label className={labelClasses}>Planned End *</label>
                <input
                  type="datetime-local"
                  value={formData.planned_end || ''}
                  onChange={(e) => handleChange('planned_end', e.target.value)}
                  className={inputClasses}
                />
                {errors.planned_end && (
                  <p className={errorClasses}>{errors.planned_end}</p>
                )}
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className={labelClasses}>Notes (Optional)</label>
              <textarea
                value={formData.notes || ''}
                onChange={(e) => handleChange('notes', e.target.value)}
                className={inputClasses}
                rows={3}
                placeholder="Add any notes or special instructions..."
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" loading={createMutation.isPending}>
            <Save className="w-4 h-4 mr-2" />
            Create Batch
          </Button>
        </div>
      </form>
    </div>
  );
}
