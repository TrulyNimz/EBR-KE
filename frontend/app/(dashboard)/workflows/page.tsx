'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { GitBranch, Layers, ArrowRight, CheckCircle2, Archive } from 'lucide-react';
import { StatusBadge } from '@/components/ui/status-badge';
import {
  getWorkflows,
  activateWorkflow,
  deprecateWorkflow,
  type WorkflowListItem,
} from '@/lib/api/workflows';

const statusVariant: Record<string, 'default' | 'primary' | 'success' | 'warning' | 'danger'> = {
  draft: 'default',
  active: 'success',
  deprecated: 'warning',
  archived: 'danger',
};

export default function WorkflowsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['workflows', statusFilter],
    queryFn: () => getWorkflows({ status: statusFilter || undefined }),
  });

  const activateMutation = useMutation({
    mutationFn: activateWorkflow,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows'] }),
  });

  const deprecateMutation = useMutation({
    mutationFn: deprecateWorkflow,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows'] }),
  });

  const workflows = data?.results ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Workflows</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage workflow definitions and their lifecycle
          </p>
        </div>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-2">
        {['', 'draft', 'active', 'deprecated'].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 text-sm rounded-lg capitalize transition-colors ${
              statusFilter === s
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {/* Workflow cards */}
      {isLoading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center text-gray-500">
          Loading workflows…
        </div>
      ) : workflows.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center text-gray-500">
          No workflows found.
        </div>
      ) : (
        <div className="space-y-4">
          {workflows.map((wf) => (
            <WorkflowCard
              key={wf.id}
              workflow={wf}
              onActivate={() => activateMutation.mutate(wf.id)}
              onDeprecate={() => deprecateMutation.mutate(wf.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function WorkflowCard({
  workflow,
  onActivate,
  onDeprecate,
}: {
  workflow: WorkflowListItem;
  onActivate: () => void;
  onDeprecate: () => void;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-5 flex items-start gap-5">
      <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600">
        <GitBranch className="h-5 w-5" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 flex-wrap">
          <Link
            href={`/workflows/${workflow.id}`}
            className="text-base font-semibold text-gray-900 dark:text-white hover:text-blue-600 transition-colors"
          >
            {workflow.name}
          </Link>
          <StatusBadge variant={statusVariant[workflow.status] ?? 'default'}>
            {workflow.status}
          </StatusBadge>
          <span className="text-xs text-gray-500 dark:text-gray-400">v{workflow.version}</span>
        </div>

        <p className="text-xs font-mono text-gray-500 dark:text-gray-400 mt-0.5">{workflow.code}</p>

        <div className="flex items-center gap-4 mt-3 text-sm text-gray-600 dark:text-gray-300">
          <span className="flex items-center gap-1">
            <Layers className="h-4 w-4 text-gray-400" />
            {workflow.state_count} state{workflow.state_count !== 1 ? 's' : ''}
          </span>
          <span className="flex items-center gap-1">
            <ArrowRight className="h-4 w-4 text-gray-400" />
            {workflow.transition_count} transition{workflow.transition_count !== 1 ? 's' : ''}
          </span>
          {workflow.applicable_record_types.length > 0 && (
            <span className="text-xs text-gray-400">
              Applies to: {workflow.applicable_record_types.join(', ')}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {workflow.status === 'draft' && (
          <button
            onClick={onActivate}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
          >
            <CheckCircle2 className="h-4 w-4" />
            Activate
          </button>
        )}
        {workflow.status === 'active' && (
          <button
            onClick={onDeprecate}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
          >
            <Archive className="h-4 w-4" />
            Deprecate
          </button>
        )}
        <Link
          href={`/workflows/${workflow.id}`}
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
        >
          View
        </Link>
      </div>
    </div>
  );
}
