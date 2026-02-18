'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Heart,
  Activity,
  ClipboardList,
  Pill,
  AlertTriangle,
  User,
  Calendar,
  BedDouble,
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/status-badge';
import {
  getPatient,
  getPatientAllergies,
  getLatestVitals,
  getMedicationOrders,
} from '@/lib/api/healthcare';

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: patient, isLoading } = useQuery({
    queryKey: ['patient', id],
    queryFn: () => getPatient(id),
  });

  const { data: allergies } = useQuery({
    queryKey: ['patient-allergies', id],
    queryFn: () => getPatientAllergies(id),
    enabled: !!id,
  });

  const { data: vitals } = useQuery({
    queryKey: ['vitals-latest', id],
    queryFn: () => getLatestVitals(id),
    enabled: !!id,
  });

  const { data: medsData } = useQuery({
    queryKey: ['medication-orders', id],
    queryFn: () => getMedicationOrders(id),
    enabled: !!id,
  });

  const activeMeds = medsData?.results.filter((m) => m.status === 'active') ?? [];

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Loading patient…</div>;
  }

  if (!patient) {
    return <div className="p-8 text-center text-red-500">Patient not found.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>

        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 text-xl font-bold">
              {patient.first_name[0]}
              {patient.last_name[0]}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {patient.full_name}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                #{patient.patient_number} · {patient.age} yrs · {patient.gender} ·{' '}
                {patient.blood_type || 'Blood type unknown'}
              </p>
            </div>
          </div>
          <StatusBadge
            variant={
              patient.status === 'active'
                ? 'success'
                : patient.status === 'discharged'
                ? 'default'
                : 'warning'
            }
          >
            {patient.status}
          </StatusBadge>
        </div>
      </div>

      {/* Admission Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <InfoCard
          icon={<BedDouble className="h-5 w-5 text-blue-600" />}
          title="Ward / Bed"
          value={patient.ward ? `${patient.ward}${patient.bed_number ? ` — ${patient.bed_number}` : ''}` : 'Not admitted'}
        />
        <InfoCard
          icon={<User className="h-5 w-5 text-purple-600" />}
          title="Attending Physician"
          value={patient.attending_physician_name || 'Unassigned'}
        />
        <InfoCard
          icon={<Calendar className="h-5 w-5 text-green-600" />}
          title="Admitted"
          value={
            patient.admission_date
              ? new Date(patient.admission_date).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })
              : 'N/A'
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Latest Vitals */}
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-600" />
            Latest Vital Signs
          </h2>
          {vitals ? (
            <div className="grid grid-cols-2 gap-3">
              <VitalItem
                label="BP"
                value={
                  vitals.systolic_bp && vitals.diastolic_bp
                    ? `${vitals.systolic_bp}/${vitals.diastolic_bp} mmHg`
                    : '—'
                }
              />
              <VitalItem
                label="Heart Rate"
                value={vitals.heart_rate ? `${vitals.heart_rate} bpm` : '—'}
              />
              <VitalItem
                label="Temp"
                value={vitals.temperature ? `${vitals.temperature} °C` : '—'}
              />
              <VitalItem
                label="O₂ Sat"
                value={vitals.oxygen_saturation ? `${vitals.oxygen_saturation}%` : '—'}
              />
              <VitalItem
                label="Resp Rate"
                value={vitals.respiratory_rate ? `${vitals.respiratory_rate}/min` : '—'}
              />
              <VitalItem
                label="Pain"
                value={vitals.pain_score !== null ? `${vitals.pain_score}/10` : '—'}
              />
              {vitals.bmi && (
                <VitalItem label="BMI" value={`${vitals.bmi.toFixed(1)}`} />
              )}
              <VitalItem
                label="Recorded"
                value={new Date(vitals.recorded_at).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              />
            </div>
          ) : (
            <p className="text-sm text-gray-500">No vital signs recorded.</p>
          )}
        </section>

        {/* Allergies */}
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            Allergies ({allergies?.length ?? 0})
          </h2>
          {!allergies || allergies.length === 0 ? (
            <p className="text-sm text-green-600 dark:text-green-400">
              No known allergies recorded.
            </p>
          ) : (
            <ul className="space-y-2">
              {allergies.map((a) => (
                <li
                  key={a.id}
                  className="flex items-start justify-between gap-3 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {a.allergen}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {a.allergen_type} · Reaction: {a.reaction || 'Unknown'}
                    </p>
                  </div>
                  <StatusBadge
                    variant={
                      a.severity === 'life_threatening' || a.severity === 'severe'
                        ? 'danger'
                        : a.severity === 'moderate'
                        ? 'warning'
                        : 'default'
                    }
                  >
                    {a.severity.replace('_', ' ')}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Active Medications */}
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Pill className="h-5 w-5 text-purple-600" />
            Active Medications ({activeMeds.length})
          </h2>
          {activeMeds.length === 0 ? (
            <p className="text-sm text-gray-500">No active medication orders.</p>
          ) : (
            <ul className="space-y-2">
              {activeMeds.map((m) => (
                <li
                  key={m.id}
                  className="py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
                >
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {m.medication_name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {m.dose} {m.dose_unit} · {m.route} · {m.frequency}
                  </p>
                  {m.special_instructions && (
                    <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-0.5">
                      ⚠ {m.special_instructions}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Clinical Notes (placeholder) */}
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-green-600" />
            Clinical Notes
          </h2>
          <p className="text-sm text-gray-500">
            Clinical notes panel — view and add SOAP notes.
          </p>
        </section>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function InfoCard({
  icon,
  title,
  value,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 flex items-center gap-4">
      <div className="p-2 rounded-lg bg-gray-50 dark:bg-gray-700">{icon}</div>
      <div>
        <p className="text-xs text-gray-500 dark:text-gray-400">{title}</p>
        <p className="text-sm font-semibold text-gray-900 dark:text-white">{value}</p>
      </div>
    </div>
  );
}

function VitalItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-sm font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}
