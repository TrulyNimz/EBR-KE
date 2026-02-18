'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  Users,
  AlertTriangle,
  Activity,
  BedDouble,
  ClipboardList,
  Pill,
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/status-badge';
import { getPatients, getAbnormalVitals } from '@/lib/api/healthcare';

export default function HealthcarePage() {
  const { data: patientsData, isLoading: patientsLoading } = useQuery({
    queryKey: ['patients', { page: 1, page_size: 5, status: 'active' }],
    queryFn: () => getPatients({ page: 1, page_size: 5, status: 'active' }),
  });

  const { data: abnormalVitals } = useQuery({
    queryKey: ['vitals', 'abnormal'],
    queryFn: () => getAbnormalVitals(),
  });

  const patients = patientsData?.results ?? [];
  const totalActive = patientsData?.count ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Healthcare</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Patient management and clinical records
          </p>
        </div>
        <Link
          href="/healthcare/patients/new"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Users className="h-4 w-4" />
          Admit Patient
        </Link>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KPICard
          icon={<BedDouble className="h-5 w-5 text-blue-600" />}
          title="Active Patients"
          value={patientsLoading ? '…' : String(totalActive)}
          color="blue"
        />
        <KPICard
          icon={<AlertTriangle className="h-5 w-5 text-red-600" />}
          title="Abnormal Vitals"
          value={abnormalVitals ? String(abnormalVitals.length) : '…'}
          color="red"
        />
        <KPICard
          icon={<Activity className="h-5 w-5 text-green-600" />}
          title="Today's Assessments"
          value="—"
          color="green"
        />
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <QuickLink
          href="/healthcare/patients"
          icon={<Users className="h-5 w-5" />}
          title="Patient Registry"
          description="View and manage all patients"
        />
        <QuickLink
          href="/healthcare/medications"
          icon={<Pill className="h-5 w-5" />}
          title="Medication Administration"
          description="MAR and 5-rights verification"
        />
        <QuickLink
          href="/healthcare/notes"
          icon={<ClipboardList className="h-5 w-5" />}
          title="Clinical Notes"
          description="SOAP notes and documentation"
        />
      </div>

      {/* Recent active patients */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Active Patients
          </h2>
          <Link href="/healthcare/patients" className="text-sm text-blue-600 hover:underline">
            View all →
          </Link>
        </div>

        {patientsLoading ? (
          <p className="text-sm text-gray-500">Loading…</p>
        ) : patients.length === 0 ? (
          <p className="text-sm text-gray-500">No active patients.</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead>
              <tr>
                {['Patient', 'Ward / Bed', 'Physician', 'Admitted', 'Status'].map((h) => (
                  <th
                    key={h}
                    className="py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider pr-4"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {patients.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="py-3 pr-4">
                    <Link
                      href={`/healthcare/patients/${p.id}`}
                      className="text-sm font-medium text-blue-600 hover:underline"
                    >
                      {p.full_name}
                    </Link>
                    <p className="text-xs text-gray-500">#{p.patient_number}</p>
                  </td>
                  <td className="py-3 pr-4 text-sm text-gray-600 dark:text-gray-300">
                    {p.ward ? `${p.ward}${p.bed_number ? ` · ${p.bed_number}` : ''}` : '—'}
                  </td>
                  <td className="py-3 pr-4 text-sm text-gray-600 dark:text-gray-300">
                    {p.attending_physician_name || '—'}
                  </td>
                  <td className="py-3 pr-4 text-sm text-gray-500">
                    {p.admission_date
                      ? new Date(p.admission_date).toLocaleDateString()
                      : '—'}
                  </td>
                  <td className="py-3">
                    <StatusBadge
                      variant={
                        p.status === 'active'
                          ? 'success'
                          : p.status === 'discharged'
                          ? 'default'
                          : 'warning'
                      }
                    >
                      {p.status}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function KPICard({
  icon,
  title,
  value,
  color,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  color: 'blue' | 'red' | 'green';
}) {
  const bg = {
    blue: 'bg-blue-50 dark:bg-blue-900/20',
    red: 'bg-red-50 dark:bg-red-900/20',
    green: 'bg-green-50 dark:bg-green-900/20',
  }[color];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className={`inline-flex p-2 rounded-lg mb-3 ${bg}`}>{icon}</div>
      <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
      <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
    </div>
  );
}

function QuickLink({
  href,
  icon,
  title,
  description,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-start gap-4 p-4 bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow"
    >
      <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-blue-600 shrink-0">
        {icon}
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-900 dark:text-white">{title}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{description}</p>
      </div>
    </Link>
  );
}
