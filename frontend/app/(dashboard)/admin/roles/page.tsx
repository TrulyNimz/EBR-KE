'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, Shield, ShieldCheck } from 'lucide-react';
import { StatusBadge } from '@/components/ui/status-badge';
import { getRoles, type Role } from '@/lib/api/users';

export default function RolesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: getRoles,
  });
  const roles = data?.results ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Roles</h1>
        <p className="text-gray-600 dark:text-gray-400">
          View roles and their assigned permissions
        </p>
      </div>

      {isLoading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center text-gray-500">
          Loading roles…
        </div>
      ) : roles.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center text-gray-500">
          No roles found.
        </div>
      ) : (
        <div className="space-y-4">
          {roles.map((role) => (
            <RoleCard key={role.id} role={role} />
          ))}
        </div>
      )}
    </div>
  );
}

function RoleCard({ role }: { role: Role }) {
  const [expanded, setExpanded] = useState(false);

  // Group permissions by module
  const byModule: Record<string, typeof role.permissions> = {};
  for (const p of role.permissions) {
    (byModule[p.module] ??= []).push(p);
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <span className="text-gray-400 dark:text-gray-500">
          {expanded ? (
            <ChevronDown className="h-5 w-5" />
          ) : (
            <ChevronRight className="h-5 w-5" />
          )}
        </span>
        <span className="text-blue-600">
          {role.is_system_role ? (
            <ShieldCheck className="h-5 w-5" />
          ) : (
            <Shield className="h-5 w-5" />
          )}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-white">{role.name}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">{role.code}</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {role.is_system_role && (
            <StatusBadge variant="purple">System</StatusBadge>
          )}
          <StatusBadge variant={role.is_active ? 'success' : 'default'}>
            {role.is_active ? 'Active' : 'Inactive'}
          </StatusBadge>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {role.permissions.length} permission{role.permissions.length !== 1 ? 's' : ''}
          </span>
        </div>
      </button>

      {/* Expanded permissions */}
      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4 space-y-4">
          {role.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{role.description}</p>
          )}
          {role.permissions.length === 0 ? (
            <p className="text-sm text-gray-500">No permissions assigned.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(byModule).sort().map(([module, perms]) => (
                <div key={module}>
                  <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                    {module}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {perms.map((p) => (
                      <span
                        key={p.id}
                        title={p.description}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 font-mono"
                      >
                        {p.resource}.{p.action}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
