'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { createUser, getRoles, type CreateUserPayload } from '@/lib/api/users';

export default function NewUserPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [form, setForm] = useState<CreateUserPayload>({
    email: '',
    employee_id: '',
    first_name: '',
    last_name: '',
    title: '',
    department: '',
    phone: '',
    password: '',
    confirm_password: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { data: rolesData } = useQuery({
    queryKey: ['roles'],
    queryFn: getRoles,
  });
  const roles = rolesData?.results ?? [];

  const mutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      router.push('/admin/users');
    },
    onError: (err: any) => {
      if (err.fieldErrors) setErrors(err.fieldErrors);
    },
  });

  function set(field: keyof CreateUserPayload, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => { const copy = { ...e }; delete copy[field]; return copy; });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const next: Record<string, string> = {};
    if (!form.email) next.email = 'Email is required';
    if (!form.first_name) next.first_name = 'First name is required';
    if (!form.last_name) next.last_name = 'Last name is required';
    if (!form.password) next.password = 'Password is required';
    if (form.password !== form.confirm_password)
      next.confirm_password = 'Passwords do not match';
    if (Object.keys(next).length) { setErrors(next); return; }
    mutation.mutate(form);
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Create User</h1>
        <p className="text-gray-600 dark:text-gray-400">Add a new user to the platform</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
        {/* Name */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="First Name" required error={errors.first_name}>
            <input
              type="text"
              value={form.first_name}
              onChange={(e) => set('first_name', e.target.value)}
              className={inputClass(!!errors.first_name)}
            />
          </Field>
          <Field label="Last Name" required error={errors.last_name}>
            <input
              type="text"
              value={form.last_name}
              onChange={(e) => set('last_name', e.target.value)}
              className={inputClass(!!errors.last_name)}
            />
          </Field>
        </div>

        {/* Email & Employee ID */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Email" required error={errors.email}>
            <input
              type="email"
              value={form.email}
              onChange={(e) => set('email', e.target.value)}
              className={inputClass(!!errors.email)}
            />
          </Field>
          <Field label="Employee ID" error={errors.employee_id}>
            <input
              type="text"
              value={form.employee_id}
              onChange={(e) => set('employee_id', e.target.value)}
              className={inputClass(!!errors.employee_id)}
            />
          </Field>
        </div>

        {/* Title & Department */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Title" error={errors.title}>
            <input
              type="text"
              placeholder="e.g. Senior Analyst"
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              className={inputClass(false)}
            />
          </Field>
          <Field label="Department" error={errors.department}>
            <input
              type="text"
              placeholder="e.g. Quality Assurance"
              value={form.department}
              onChange={(e) => set('department', e.target.value)}
              className={inputClass(false)}
            />
          </Field>
        </div>

        {/* Phone */}
        <Field label="Phone" error={errors.phone}>
          <input
            type="tel"
            value={form.phone}
            onChange={(e) => set('phone', e.target.value)}
            className={inputClass(false)}
          />
        </Field>

        <hr className="border-gray-200 dark:border-gray-700" />

        {/* Password */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Password" required error={errors.password}>
            <input
              type="password"
              value={form.password}
              onChange={(e) => set('password', e.target.value)}
              className={inputClass(!!errors.password)}
            />
          </Field>
          <Field label="Confirm Password" required error={errors.confirm_password}>
            <input
              type="password"
              value={form.confirm_password}
              onChange={(e) => set('confirm_password', e.target.value)}
              className={inputClass(!!errors.confirm_password)}
            />
          </Field>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          The user will be prompted to change their password on first login.
        </p>

        {/* Server error */}
        {mutation.isError && !Object.keys(errors).length && (
          <p className="text-sm text-red-600 dark:text-red-400">
            {(mutation.error as any)?.message || 'Failed to create user. Please try again.'}
          </p>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? 'Creating…' : 'Create User'}
          </Button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function Field({
  label,
  required,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}

function inputClass(hasError: boolean) {
  return `w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 ${
    hasError
      ? 'border-red-500 dark:border-red-400'
      : 'border-gray-300 dark:border-gray-600'
  }`;
}
