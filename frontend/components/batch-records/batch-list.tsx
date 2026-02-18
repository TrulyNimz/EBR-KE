'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Search, Plus, Filter, Download } from 'lucide-react';
import { DataTable, type Column } from '@/components/ui/data-table';
import { BatchStatusBadge } from '@/components/ui/status-badge';
import { Button } from '@/components/ui/button';
import { getBatches } from '@/lib/api/batch-records';
import type { Batch, BatchStatus, BatchListParams } from '@/types/batch-records';

const PAGE_SIZE = 10;

export function BatchList() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<BatchStatus | ''>('');
  const [sortField, setSortField] = useState('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const params: BatchListParams = {
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    status: statusFilter || undefined,
    ordering: sortDirection === 'desc' ? `-${sortField}` : sortField,
  };

  const { data, isLoading } = useQuery({
    queryKey: ['batches', params],
    queryFn: () => getBatches(params),
  });

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const columns: Column<Batch>[] = [
    {
      key: 'batch_number',
      header: 'Batch Number',
      sortable: true,
      render: (batch) => (
        <span className="font-medium text-blue-600 dark:text-blue-400">
          {batch.batch_number}
        </span>
      ),
    },
    {
      key: 'product_name',
      header: 'Product',
      sortable: true,
      render: (batch) => (
        <div>
          <div className="font-medium">{batch.product_name}</div>
          <div className="text-xs text-gray-500">{batch.product_code}</div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (batch) => <BatchStatusBadge status={batch.status} />,
    },
    {
      key: 'planned_quantity',
      header: 'Quantity',
      render: (batch) => (
        <span>
          {batch.actual_quantity ?? batch.planned_quantity} {batch.unit_of_measure}
        </span>
      ),
    },
    {
      key: 'completion_percentage',
      header: 'Progress',
      render: (batch) => (
        <div className="w-24">
          <div className="flex items-center">
            <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${batch.completion_percentage}%` }}
              />
            </div>
            <span className="ml-2 text-xs text-gray-500">
              {batch.completion_percentage}%
            </span>
          </div>
        </div>
      ),
    },
    {
      key: 'planned_start',
      header: 'Planned Start',
      sortable: true,
      render: (batch) => new Date(batch.planned_start).toLocaleDateString(),
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (batch) => new Date(batch.created_at).toLocaleDateString(),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Batch Records
        </h1>
        <Button onClick={() => router.push('/batch-records/new')}>
          <Plus className="w-4 h-4 mr-2" />
          New Batch
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search batches..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as BatchStatus | '');
            setPage(1);
          }}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="on_hold">On Hold</option>
          <option value="cancelled">Cancelled</option>
        </select>

        <Button variant="outline">
          <Filter className="w-4 h-4 mr-2" />
          More Filters
        </Button>

        <Button variant="outline">
          <Download className="w-4 h-4 mr-2" />
          Export
        </Button>
      </div>

      {/* Data Table */}
      <DataTable
        data={data?.results || []}
        columns={columns}
        keyExtractor={(batch) => batch.id}
        loading={isLoading}
        pagination={
          data
            ? {
                page,
                pageSize: PAGE_SIZE,
                total: data.count,
                onPageChange: setPage,
              }
            : undefined
        }
        sorting={{
          field: sortField,
          direction: sortDirection,
          onSort: handleSort,
        }}
        onRowClick={(batch) => router.push(`/batch-records/${batch.id}`)}
        emptyMessage="No batch records found"
      />
    </div>
  );
}
