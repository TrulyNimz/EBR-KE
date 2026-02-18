'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { createPatient, type CreatePatientPayload, type PatientGender } from '@/lib/api/healthcare';

export default function NewPatientPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [form, setForm] = useState<CreatePatientPayload>({
    patient_number: '',
    first_name: '',
    middle_name: '',
    last_name: '',
    date_of_birth: '',
    gender: 'unknown',
    blood_type: '',
    ward: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const mutation = useMutation({
    mutationFn: createPatient,
    onSuccess: (patient) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      router.push(`/healthcare/patients/${patient.id}`);
    },
    onError: (err: any) => {
      if (err.fieldErrors) setErrors(err.fieldErrors);
    },
  });

  function set<K extends keyof CreatePatientPayload>(field: K, value: CreatePatientPayload[K]) {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => { const copy = { ...e }; delete copy[field as string]; return copy; });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const next: Record<string, string> = {};
    if (!form.patient_number) next.patient_number = 'Patient number is required';
    if (!form.first_name) next.first_name = 'First name is required';
    if (!form.last_name) next.last_name = 'Last name is required';
    if (!form.date_of_birth) next.date_of_birth = 'Date of birth is required';
    if (Object.keys(next).length) { setErrors(next); return; }
    mutation.mutate(form);
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Register Patient</h1>
        <p className="text-gray-600 dark:text-gray-400">Add a new patient to the registry</p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6"
      >
        {/* Patient number */}
        <Field label="Patient Number" required error={errors.patient_number}>
          <input
            type="text"
            placeholder="e.g. P-2024-001"
            value={form.patient_number}
            onChange={(e) => set('patient_number', e.target.value)}
            className={inputClass(!!errors.patient_number)}
          />
        </Field>

        {/* Name */}
        <div className="grid grid-cols-3 gap-4">
          <Field label="First Name" required error={errors.first_name}>
            <input
              type="text"
              value={form.first_name}
              onChange={(e) => set('first_name', e.target.value)}
              className={inputClass(!!errors.first_name)}
            />
          </Field>
          <Field label="Middle Name">
            <input
              type="text"
              value={form.middle_name}
              onChange={(e) => set('middle_name', e.target.value)}
              className={inputClass(false)}
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

        {/* DOB & Gender */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Date of Birth" required error={errors.date_of_birth}>
            <input
              type="date"
              value={form.date_of_birth}
              onChange={(e) => set('date_of_birth', e.target.value)}
              className={inputClass(!!errors.date_of_birth)}
            />
          </Field>
          <Field label="Gender">
            <select
              value={form.gender}
              onChange={(e) => set('gender', e.target.value as PatientGender)}
              className={inputClass(false)}
            >
              <option value="unknown">Unknown</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </Field>
        </div>

        {/* Blood type & ward */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Blood Type">
            <select
              value={form.blood_type}
              onChange={(e) => set('blood_type', e.target.value)}
              className={inputClass(false)}
            >
              <option value="">Unknown</option>
              {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map((bt) => (
                <option key={bt} value={bt}>{bt}</option>
              ))}
            </select>
          </Field>
          <Field label="Ward (optional)">
            <input
              type="text"
              placeholder="e.g. General Ward A"
              value={form.ward}
              onChange={(e) => set('ward', e.target.value)}
              className={inputClass(false)}
            />
          </Field>
        </div>

        {mutation.isError && !Object.keys(errors).length && (
          <p className="text-sm text-red-600 dark:text-red-400">
            {(mutation.error as any)?.message || 'Failed to register patient.'}
          </p>
        )}

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? 'Registering…' : 'Register Patient'}
          </Button>
        </div>
      </form>
    </div>
  );
}

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
