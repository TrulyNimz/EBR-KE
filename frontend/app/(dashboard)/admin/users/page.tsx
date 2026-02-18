'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Search,
  Lock,
  Unlock,
  KeyRound,
  MoreVertical,
  UserCheck,
  UserX,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/ui/status-badge';
import {
  getUsers,
  lockUser,
  unlockUser,
  forcePasswordReset,
  type UserListItem,
} from '@/lib/api/users';

const PAGE_SIZE = 20;

export default function UsersPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [actionTarget, setActionTarget] = useState<string | null>(null);

  const params = {
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    is_active: activeFilter === 'all' ? undefined : activeFilter === 'active',
  };

  const { data, isLoading } = useQuery({
    queryKey: ['users', params],
    queryFn: () => getUsers(params),
  });

  const lockMutation = useMutation({
    mutationFn: lockUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  });

  const unlockMutation = useMutation({
    mutationFn: unlockUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  });

  const resetMutation = useMutation({
    mutationFn: forcePasswordReset,
    onSuccess: () => setActionTarget(null),
  });

  const users = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Users</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage platform users and their access
          </p>
        </div>
        <Button onClick={() => router.push('/admin/users/new')}>
          <Plus className="h-4 w-4 mr-2" />
          New User
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name, email, or employee ID…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex gap-2">
          {(['all', 'active', 'inactive'] as const).map((f) => (
            <button
              key={f}
              onClick={() => { setActiveFilter(f); setPage(1); }}
              className={`px-3 py-2 text-sm rounded-lg capitalize transition-colors ${
                activeFilter === f
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading users…</div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No users found.</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                {['Name', 'Department', 'Roles', 'Status', 'Last Login', ''].map((h) => (
                  <th
                    key={h}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {users.map((user) => (
                <UserRow
                  key={user.id}
                  user={user}
                  onLock={() => lockMutation.mutate(user.id)}
                  onUnlock={() => unlockMutation.mutate(user.id)}
                  onResetPassword={() => resetMutation.mutate(user.id)}
                  actionMenuOpen={actionTarget === user.id}
                  onToggleMenu={() =>
                    setActionTarget(actionTarget === user.id ? null : user.id)
                  }
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
          <span>
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, totalCount)} of{' '}
            {totalCount} users
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              className="px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page === totalPages}
              className="px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// UserRow
// ---------------------------------------------------------------------------

function UserRow({
  user,
  onLock,
  onUnlock,
  onResetPassword,
  actionMenuOpen,
  onToggleMenu,
}: {
  user: UserListItem;
  onLock: () => void;
  onUnlock: () => void;
  onResetPassword: () => void;
  actionMenuOpen: boolean;
  onToggleMenu: () => void;
}) {
  return (
    <tr className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
      <td className="px-6 py-4">
        <div>
          <Link
            href={`/admin/users/${user.id}`}
            className="text-sm font-medium text-blue-600 hover:underline"
          >
            {user.full_name}
          </Link>
          <p className="text-xs text-gray-500 dark:text-gray-400">{user.email}</p>
          {user.employee_id && (
            <p className="text-xs text-gray-400 dark:text-gray-500">#{user.employee_id}</p>
          )}
        </div>
      </td>
      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
        {user.department || '—'}
      </td>
      <td className="px-6 py-4">
        <div className="flex flex-wrap gap-1">
          {user.roles.length > 0 ? (
            user.roles.map((r) => (
              <StatusBadge key={r} variant="info">
                {r}
              </StatusBadge>
            ))
          ) : (
            <span className="text-xs text-gray-400">No roles</span>
          )}
        </div>
      </td>
      <td className="px-6 py-4">
        <div className="flex flex-col gap-1">
          <StatusBadge variant={user.is_active ? 'success' : 'default'}>
            {user.is_active ? 'Active' : 'Inactive'}
          </StatusBadge>
          {user.is_locked && (
            <StatusBadge variant="danger">Locked</StatusBadge>
          )}
          {user.mfa_enabled && (
            <StatusBadge variant="primary">MFA</StatusBadge>
          )}
        </div>
      </td>
      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
        {user.last_login
          ? new Date(user.last_login).toLocaleDateString()
          : 'Never'}
      </td>
      <td className="px-6 py-4 text-right">
        <div className="relative inline-block">
          <button
            onClick={onToggleMenu}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500"
          >
            <MoreVertical className="h-4 w-4" />
          </button>
          {actionMenuOpen && (
            <div className="absolute right-0 mt-1 w-44 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
              {user.is_locked ? (
                <MenuAction icon={<Unlock className="h-4 w-4" />} label="Unlock Account" onClick={onUnlock} />
              ) : (
                <MenuAction icon={<Lock className="h-4 w-4" />} label="Lock Account" onClick={onLock} />
              )}
              <MenuAction
                icon={<KeyRound className="h-4 w-4" />}
                label="Force Password Reset"
                onClick={onResetPassword}
              />
              {user.is_active ? (
                <MenuAction
                  icon={<UserX className="h-4 w-4" />}
                  label="Deactivate"
                  onClick={() => {}}
                  danger
                />
              ) : (
                <MenuAction
                  icon={<UserCheck className="h-4 w-4" />}
                  label="Activate"
                  onClick={() => {}}
                />
              )}
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

function MenuAction({
  icon,
  label,
  onClick,
  danger,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 w-full px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 ${
        danger ? 'text-red-600' : 'text-gray-700 dark:text-gray-300'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
