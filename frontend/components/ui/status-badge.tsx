'use client';

import { cva, type VariantProps } from 'class-variance-authority';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
  {
    variants: {
      variant: {
        default: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
        primary: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
        success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
        danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
        info: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-300',
        purple: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface StatusBadgeProps extends VariantProps<typeof badgeVariants> {
  children: React.ReactNode;
  className?: string;
}

export function StatusBadge({ variant, children, className }: StatusBadgeProps) {
  return (
    <span className={badgeVariants({ variant, className })}>
      {children}
    </span>
  );
}

// Pre-configured status badges for common use cases
export type BatchStatus = 'draft' | 'in_progress' | 'completed' | 'cancelled' | 'on_hold';
export type StepStatus = 'pending' | 'in_progress' | 'completed' | 'skipped' | 'failed';

const batchStatusConfig: Record<BatchStatus, { label: string; variant: StatusBadgeProps['variant'] }> = {
  draft: { label: 'Draft', variant: 'default' },
  in_progress: { label: 'In Progress', variant: 'primary' },
  completed: { label: 'Completed', variant: 'success' },
  cancelled: { label: 'Cancelled', variant: 'danger' },
  on_hold: { label: 'On Hold', variant: 'warning' },
};

const stepStatusConfig: Record<StepStatus, { label: string; variant: StatusBadgeProps['variant'] }> = {
  pending: { label: 'Pending', variant: 'default' },
  in_progress: { label: 'In Progress', variant: 'primary' },
  completed: { label: 'Completed', variant: 'success' },
  skipped: { label: 'Skipped', variant: 'info' },
  failed: { label: 'Failed', variant: 'danger' },
};

export function BatchStatusBadge({ status }: { status: BatchStatus }) {
  const config = batchStatusConfig[status] || batchStatusConfig.draft;
  return <StatusBadge variant={config.variant}>{config.label}</StatusBadge>;
}

export function StepStatusBadge({ status }: { status: StepStatus }) {
  const config = stepStatusConfig[status] || stepStatusConfig.pending;
  return <StatusBadge variant={config.variant}>{config.label}</StatusBadge>;
}
