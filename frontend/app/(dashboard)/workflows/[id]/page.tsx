'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Shield, ArrowRight, Layers, Tag } from 'lucide-react';
import { WorkflowVisualizer } from '@/components/shared/workflow/workflow-visualizer';
import { StatusBadge } from '@/components/ui/status-badge';
import { getWorkflow } from '@/lib/api/workflows';

const statusVariant: Record<string, 'default' | 'primary' | 'success' | 'warning' | 'danger'> = {
  draft: 'default',
  active: 'success',
  deprecated: 'warning',
  archived: 'danger',
};

export default function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: workflow, isLoading, isError } = useQuery({
    queryKey: ['workflow', id],
    queryFn: () => getWorkflow(id),
  });

  if (isLoading) {
    return (
      <div className="p-8 text-center text-gray-500">Loading workflow…</div>
    );
  }

  if (isError || !workflow) {
    return (
      <div className="p-8 text-center text-red-500">Failed to load workflow.</div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Workflows
        </button>

        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {workflow.name}
              </h1>
              <StatusBadge variant={statusVariant[workflow.status] ?? 'default'}>
                {workflow.status}
              </StatusBadge>
              <span className="text-sm text-gray-500 dark:text-gray-400">v{workflow.version}</span>
            </div>
            <p className="text-sm font-mono text-gray-500 dark:text-gray-400 mt-1">
              {workflow.code}
            </p>
            {workflow.description && (
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">
                {workflow.description}
              </p>
            )}
          </div>

          {workflow.applicable_record_types.length > 0 && (
            <div className="flex items-center gap-1.5 shrink-0">
              <Tag className="h-4 w-4 text-gray-400" />
              <div className="flex flex-wrap gap-1">
                {workflow.applicable_record_types.map((t) => (
                  <StatusBadge key={t} variant="info">{t}</StatusBadge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Workflow Visualizer */}
      <WorkflowVisualizer
        states={workflow.states}
        transitions={workflow.transitions}
      />

      {/* States Detail */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
          <Layers className="h-5 w-5" />
          States ({workflow.states.length})
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...workflow.states].sort((a, b) => a.order - b.order).map((state) => (
            <div
              key={state.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4"
              style={{ borderLeftColor: state.color || '#6B7280' }}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">
                  {state.name}
                </p>
                <div className="flex gap-1">
                  {state.is_initial && <StatusBadge variant="primary">Initial</StatusBadge>}
                  {state.is_terminal && <StatusBadge variant="success">Terminal</StatusBadge>}
                </div>
              </div>
              <p className="text-xs font-mono text-gray-500 dark:text-gray-400">{state.code}</p>
              {state.description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{state.description}</p>
              )}
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                {state.required_signatures > 0 && (
                  <span className="flex items-center gap-1">
                    <Shield className="h-3 w-3" />
                    {state.required_signatures} signature{state.required_signatures !== 1 ? 's' : ''}
                  </span>
                )}
                <span className="capitalize">{state.state_type.replace('_', ' ')}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Transitions Detail */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
          <ArrowRight className="h-5 w-5" />
          Transitions ({workflow.transitions.length})
        </h2>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                {['Transition', 'From', 'To', 'Requires', 'Permission'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {[...workflow.transitions]
                .sort((a, b) => a.order - b.order)
                .map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {t.name}
                      </p>
                      <p className="text-xs font-mono text-gray-400">{t.code}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                      {t.from_state_name}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                      {t.to_state_name}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {t.requires_approval && (
                          <StatusBadge variant="warning">Approval</StatusBadge>
                        )}
                        {t.required_roles.map((r) => (
                          <StatusBadge key={r} variant="info">{r}</StatusBadge>
                        ))}
                        {!t.requires_approval && t.required_roles.length === 0 && (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-gray-500 dark:text-gray-400">
                      {t.required_permission || '—'}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
