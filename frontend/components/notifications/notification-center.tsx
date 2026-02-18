/**
 * Full notification center component.
 */
'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  Bell,
  CheckCheck,
  Filter,
  Loader2,
  Search,
  X,
} from 'lucide-react';
import { useNotificationStore } from '@/stores/notification-store';
import { NotificationItem } from './notification-item';
import {
  NotificationCategory,
  NotificationPriority,
  NotificationStatus,
} from '@/types/notifications';
import { cn } from '@/lib/utils';

const categories: { value: NotificationCategory | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'general', label: 'General' },
  { value: 'workflow', label: 'Workflow' },
  { value: 'approval', label: 'Approvals' },
  { value: 'alert', label: 'Alerts' },
  { value: 'reminder', label: 'Reminders' },
  { value: 'system', label: 'System' },
];

const statuses: { value: NotificationStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'sent', label: 'Unread' },
  { value: 'read', label: 'Read' },
];

const priorities: { value: NotificationPriority | 'all'; label: string }[] = [
  { value: 'all', label: 'All Priorities' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'high', label: 'High' },
  { value: 'normal', label: 'Normal' },
  { value: 'low', label: 'Low' },
];

export function NotificationCenter() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [selectedCategory, setSelectedCategory] = useState<NotificationCategory | 'all'>('all');
  const [selectedStatus, setSelectedStatus] = useState<NotificationStatus | 'all'>('all');
  const [selectedPriority, setSelectedPriority] = useState<NotificationPriority | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const {
    notifications,
    isLoading,
    summary,
    fetchNotifications,
    fetchSummary,
    markSingleAsRead,
    markAllAsRead,
    markAsRead,
  } = useNotificationStore();

  // Fetch notifications and summary on mount
  useEffect(() => {
    fetchNotifications();
    fetchSummary();
  }, [fetchNotifications, fetchSummary]);

  // Filter notifications client-side
  const filteredNotifications = notifications.filter((notification) => {
    if (selectedCategory !== 'all' && notification.category !== selectedCategory) {
      return false;
    }
    if (selectedStatus !== 'all') {
      if (selectedStatus === 'sent' && notification.status === 'read') {
        return false;
      }
      if (selectedStatus === 'read' && notification.status !== 'read') {
        return false;
      }
    }
    if (selectedPriority !== 'all' && notification.priority !== selectedPriority) {
      return false;
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        notification.title.toLowerCase().includes(query) ||
        notification.message.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const unreadFiltered = filteredNotifications.filter((n) => n.status !== 'read');

  const handleMarkSelectedAsRead = () => {
    const unreadIds = unreadFiltered.map((n) => n.id);
    if (unreadIds.length > 0) {
      markAsRead(unreadIds);
    }
  };

  const clearFilters = () => {
    setSelectedCategory('all');
    setSelectedStatus('all');
    setSelectedPriority('all');
    setSearchQuery('');
  };

  const hasFilters =
    selectedCategory !== 'all' ||
    selectedStatus !== 'all' ||
    selectedPriority !== 'all' ||
    searchQuery !== '';

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
        <p className="text-gray-600 mt-1">
          Stay updated with important alerts and messages
        </p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg border p-4">
            <p className="text-sm text-gray-500">Total</p>
            <p className="text-2xl font-bold text-gray-900">{summary.total}</p>
          </div>
          <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
            <p className="text-sm text-blue-600">Unread</p>
            <p className="text-2xl font-bold text-blue-700">
              {(summary.status_counts.sent || 0) + (summary.status_counts.delivered || 0)}
            </p>
          </div>
          <div className="bg-orange-50 rounded-lg border border-orange-200 p-4">
            <p className="text-sm text-orange-600">High Priority</p>
            <p className="text-2xl font-bold text-orange-700">
              {summary.high_priority_unread}
            </p>
          </div>
          <div className="bg-green-50 rounded-lg border border-green-200 p-4">
            <p className="text-sm text-green-600">Read</p>
            <p className="text-2xl font-bold text-green-700">
              {summary.status_counts.read || 0}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg border p-4 mb-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search notifications..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value as NotificationCategory | 'all')}
            className="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {categories.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value as NotificationStatus | 'all')}
            className="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {statuses.map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </select>

          {/* Priority Filter */}
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value as NotificationPriority | 'all')}
            className="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {priorities.map((priority) => (
              <option key={priority.value} value={priority.value}>
                {priority.label}
              </option>
            ))}
          </select>
        </div>

        {/* Active Filters */}
        {hasFilters && (
          <div className="flex items-center gap-2 mt-3 pt-3 border-t">
            <span className="text-sm text-gray-500">Filters:</span>
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200"
            >
              Clear all
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-600">
          Showing {filteredNotifications.length} notification
          {filteredNotifications.length !== 1 ? 's' : ''}
          {unreadFiltered.length > 0 && (
            <span className="ml-1">({unreadFiltered.length} unread)</span>
          )}
        </p>
        <div className="flex items-center gap-2">
          {unreadFiltered.length > 0 && (
            <button
              onClick={handleMarkSelectedAsRead}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <CheckCheck className="h-4 w-4" />
              Mark visible as read
            </button>
          )}
          {notifications.some((n) => n.status !== 'read') && (
            <button
              onClick={markAllAsRead}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
            >
              <CheckCheck className="h-4 w-4" />
              Mark all as read
            </button>
          )}
        </div>
      </div>

      {/* Notifications List */}
      <div className="bg-white rounded-lg border overflow-hidden">
        {isLoading && notifications.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <Bell className="h-16 w-16 text-gray-300 mb-4" />
            {hasFilters ? (
              <>
                <p className="text-lg font-medium text-gray-700">
                  No matching notifications
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Try adjusting your filters
                </p>
                <button
                  onClick={clearFilters}
                  className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Clear filters
                </button>
              </>
            ) : (
              <>
                <p className="text-lg font-medium text-gray-700">
                  No notifications yet
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  We'll notify you when something important happens
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredNotifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onMarkRead={markSingleAsRead}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
