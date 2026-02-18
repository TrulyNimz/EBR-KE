'use client';

import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  CheckCircle2,
  Clock,
  FileText,
  Layers,
  AlertCircle,
  TrendingUp,
  Calendar,
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { BatchStatusBadge } from '@/components/ui/status-badge';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RecentBatch {
  id: string;
  batch_number: string;
  name: string;
  status: string;
  product_code: string;
  created_at: string;
  created_by_name: string;
}

interface UpcomingBatch {
  id: string;
  batch_number: string;
  name: string;
  product_code: string;
  scheduled_start: string | null;
}

interface DashboardSummary {
  batches: {
    total: number;
    active: number;
    pending_review: number;
    completed: number;
    draft: number;
    cancelled: number;
  };
  activity: {
    created_last_30_days: number;
    completed_last_30_days: number;
  };
  recent_batches: RecentBatch[];
  upcoming_batches: UpcomingBatch[];
  pending_approvals: number;
  active_templates: number;
}

function getDashboardSummary(): Promise<DashboardSummary> {
  return apiClient.get('/api/v1/dashboard/summary/');
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const { data: session } = useSession();
  const { data: summary, isLoading, isError } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: getDashboardSummary,
    refetchInterval: 60_000, // auto-refresh every minute
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Welcome back, {session?.user?.name || 'User'}
        </p>
      </div>

      {isError && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 text-sm text-red-700 dark:text-red-400 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Failed to load dashboard data. Please refresh the page.
        </div>
      )}

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          icon={<Activity className="h-5 w-5 text-blue-600" />}
          title="Active Batches"
          value={isLoading ? '…' : String(summary?.batches.active ?? 0)}
          sub={isLoading ? '' : `${summary?.batches.total ?? 0} total`}
          color="blue"
        />
        <KPICard
          icon={<AlertCircle className="h-5 w-5 text-yellow-600" />}
          title="Pending Approvals"
          value={isLoading ? '…' : String(summary?.pending_approvals ?? 0)}
          sub={isLoading ? '' : `${summary?.batches.pending_review ?? 0} under review`}
          color="yellow"
        />
        <KPICard
          icon={<CheckCircle2 className="h-5 w-5 text-green-600" />}
          title="Completed (30 days)"
          value={isLoading ? '…' : String(summary?.activity.completed_last_30_days ?? 0)}
          sub={isLoading ? '' : `${summary?.activity.created_last_30_days ?? 0} created`}
          color="green"
        />
        <KPICard
          icon={<FileText className="h-5 w-5 text-gray-600" />}
          title="Draft Batches"
          value={isLoading ? '…' : String(summary?.batches.draft ?? 0)}
          sub={isLoading ? '' : `${summary?.active_templates ?? 0} active templates`}
          color="gray"
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <QuickActionButton label="New Batch Record" href="/batch-records/new" icon={<Layers className="h-4 w-4" />} />
          <QuickActionButton label="Pending Approvals" href="/approvals" icon={<Clock className="h-4 w-4" />} />
          <QuickActionButton label="View Reports" href="/reports" icon={<TrendingUp className="h-4 w-4" />} />
          <QuickActionButton label="Settings" href="/settings" icon={<FileText className="h-4 w-4" />} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Recent Batches
          </h2>

          {isLoading ? (
            <SkeletonRows count={4} />
          ) : summary?.recent_batches.length ? (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700">
              {summary.recent_batches.map((b) => (
                <li key={b.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <Link
                      href={`/batch-records/${b.id}`}
                      className="text-sm font-medium text-blue-600 hover:underline truncate block"
                    >
                      {b.batch_number}
                    </Link>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{b.name}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      by {b.created_by_name} · {formatRelative(b.created_at)}
                    </p>
                  </div>
                  <BatchStatusBadge status={b.status as any} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">No recent batches in the last 7 days.</p>
          )}

          {!isLoading && (
            <Link
              href="/batch-records"
              className="mt-4 block text-sm text-blue-600 hover:underline"
            >
              View all batches →
            </Link>
          )}
        </div>

        {/* Upcoming Batches */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Upcoming Batches
          </h2>

          {isLoading ? (
            <SkeletonRows count={4} />
          ) : summary?.upcoming_batches.length ? (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700">
              {summary.upcoming_batches.map((b) => (
                <li key={b.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <Link
                      href={`/batch-records/${b.id}`}
                      className="text-sm font-medium text-blue-600 hover:underline truncate block"
                    >
                      {b.batch_number}
                    </Link>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{b.name}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">{b.product_code}</p>
                  </div>
                  {b.scheduled_start && (
                    <span className="shrink-0 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDate(b.scheduled_start)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">No batches scheduled for the next 7 days.</p>
          )}
        </div>
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
  sub,
  color,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  sub: string;
  color: 'blue' | 'yellow' | 'green' | 'gray';
}) {
  const bg = {
    blue: 'bg-blue-50 dark:bg-blue-900/20',
    yellow: 'bg-yellow-50 dark:bg-yellow-900/20',
    green: 'bg-green-50 dark:bg-green-900/20',
    gray: 'bg-gray-50 dark:bg-gray-700/40',
  }[color];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className={`inline-flex p-2 rounded-lg mb-3 ${bg}`}>{icon}</div>
      <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
      <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function QuickActionButton({
  label,
  href,
  icon,
}: {
  label: string;
  href: string;
  icon: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="flex flex-col items-center justify-center gap-2 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
    >
      <span className="text-gray-600 dark:text-gray-300">{icon}</span>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 text-center">
        {label}
      </span>
    </Link>
  );
}

function SkeletonRows({ count }: { count: number }) {
  return (
    <ul className="divide-y divide-gray-100 dark:divide-gray-700">
      {Array.from({ length: count }).map((_, i) => (
        <li key={i} className="py-3 flex items-center gap-4 animate-pulse">
          <div className="flex-1 space-y-1.5">
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
            <div className="h-2.5 bg-gray-100 dark:bg-gray-600 rounded w-2/3" />
          </div>
          <div className="h-5 w-16 bg-gray-200 dark:bg-gray-700 rounded-full" />
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
