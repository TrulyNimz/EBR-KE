'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Play,
  CheckCircle,
  Clock,
  User,
  FileText,
  AlertTriangle,
  Paperclip,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { BatchStatusBadge, StepStatusBadge } from '@/components/ui/status-badge';
import { StepExecutionForm } from './step-execution-form';
import { SignatureCapture } from './signature-capture';
import { getBatch, startBatch, completeBatch } from '@/lib/api/batch-records';
import type { Batch, BatchStep } from '@/types/batch-records';

interface BatchDetailProps {
  batchId: string;
}

export function BatchDetail({ batchId }: BatchDetailProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedStep, setSelectedStep] = useState<BatchStep | null>(null);
  const [showSignature, setShowSignature] = useState(false);

  // BatchSerializer nests steps directly on the batch object — no separate records call needed.
  const { data: batch, isLoading: batchLoading } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => getBatch(batchId),
  });

  const startMutation = useMutation({
    mutationFn: () => startBatch(batchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
    },
  });

  const completeMutation = useMutation({
    mutationFn: () => completeBatch(batchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
    },
  });

  if (batchLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!batch) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Batch not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {batch.batch_number}
              </h1>
              <BatchStatusBadge status={batch.status} />
            </div>
            <p className="text-gray-500">
              {batch.product_name} ({batch.product_code})
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {batch.status === 'draft' && (
            <Button
              onClick={() => startMutation.mutate()}
              loading={startMutation.isPending}
            >
              <Play className="w-4 h-4 mr-2" />
              Start Batch
            </Button>
          )}
          {batch.status === 'in_progress' && (
            <Button
              variant="success"
              onClick={() => completeMutation.mutate()}
              loading={completeMutation.isPending}
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Complete Batch
            </Button>
          )}
        </div>
      </div>

      {/* Batch Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <InfoCard
          icon={<FileText className="w-5 h-5 text-blue-500" />}
          label="Quantity"
          value={`${batch.actual_quantity ?? batch.planned_quantity} ${batch.quantity_unit}`}
        />
        <InfoCard
          icon={<Clock className="w-5 h-5 text-green-500" />}
          label="Scheduled Start"
          value={batch.scheduled_start
            ? new Date(batch.scheduled_start).toLocaleDateString()
            : 'Not set'}
        />
        <InfoCard
          icon={<User className="w-5 h-5 text-purple-500" />}
          label="Created By"
          value={batch.created_by_name}
        />
        <InfoCard
          icon={<AlertTriangle className="w-5 h-5 text-yellow-500" />}
          label="Progress"
          value={`${batch.completion_percentage}%`}
        />
      </div>

      {/* Progress Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Overall Progress
          </span>
          <span className="text-sm text-gray-500">
            {batch.completion_percentage}% Complete
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all duration-300"
            style={{ width: `${batch.completion_percentage}%` }}
          />
        </div>
      </div>

      {/* Steps Section — steps are nested directly on the batch by BatchSerializer */}
      {batch.steps.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Batch Steps
            </h2>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {batch.steps.map((step, index) => (
              <StepRow
                key={step.id}
                step={step}
                index={index + 1}
                isSelected={selectedStep?.id === step.id}
                onSelect={() => setSelectedStep(step)}
                disabled={batch.status !== 'in_progress'}
              />
            ))}
          </div>
        </div>
      )}

      {/* Step Execution Modal */}
      {selectedStep && !showSignature && (
        <StepExecutionForm
          batchId={batchId}
          step={selectedStep}
          onClose={() => setSelectedStep(null)}
          onComplete={(requiresSignature) => {
            if (requiresSignature) {
              setShowSignature(true);
            } else {
              setSelectedStep(null);
              queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
            }
          }}
        />
      )}

      {/* Signature Modal */}
      {selectedStep && showSignature && (
        <SignatureCapture
          stepId={selectedStep.id}
          meaning={selectedStep.signature_meaning}
          onClose={() => {
            setShowSignature(false);
            setSelectedStep(null);
          }}
          onComplete={() => {
            setShowSignature(false);
            setSelectedStep(null);
            queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
          }}
        />
      )}

      {/* Attachments */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Attachments
          </h2>
          <Button variant="outline" size="sm">
            <Paperclip className="w-4 h-4 mr-2" />
            Add Attachment
          </Button>
        </div>
        {batch.attachments.length === 0 ? (
          <p className="text-gray-500 text-sm">No attachments yet</p>
        ) : (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {batch.attachments.map((att) => (
              <li key={att.id} className="py-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Paperclip className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-900 dark:text-white">{att.filename}</span>
                  <span className="text-xs text-gray-500">
                    ({(att.file_size / 1024).toFixed(1)} KB)
                  </span>
                </div>
                <a
                  href={att.file}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline"
                >
                  Download
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Description */}
      {batch.description && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Description
          </h2>
          <p className="text-gray-600 dark:text-gray-400">{batch.description}</p>
        </div>
      )}
    </div>
  );
}

function InfoCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {value}
          </p>
        </div>
      </div>
    </div>
  );
}

function StepRow({
  step,
  index,
  isSelected,
  onSelect,
  disabled,
}: {
  step: BatchStep;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
  disabled: boolean;
}) {
  const canExecute = step.can_start || step.status === 'in_progress';

  return (
    <div
      className={`flex items-center justify-between p-4 ${
        isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : ''
      } ${canExecute && !disabled ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700' : ''}`}
      onClick={() => canExecute && !disabled && onSelect()}
    >
      <div className="flex items-center gap-4">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
            step.status === 'completed'
              ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
              : step.status === 'in_progress'
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
          }`}
        >
          {step.status === 'completed' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            index
          )}
        </div>
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{step.name}</p>
          <p className="text-sm text-gray-500">{step.description}</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        {step.requires_signature && (
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <FileText className="w-3 h-3" />
            Signature Required
          </span>
        )}
        <StepStatusBadge status={step.status} />
      </div>
    </div>
  );
}
