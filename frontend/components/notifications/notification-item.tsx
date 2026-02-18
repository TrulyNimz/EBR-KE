/**
 * Individual notification item component.
 */
'use client';

import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';
import {
  Bell,
  CheckCircle,
  AlertTriangle,
  Clock,
  FileText,
  Settings,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Notification,
  NotificationCategory,
  NotificationPriority,
} from '@/types/notifications';

interface NotificationItemProps {
  notification: Notification;
  onMarkRead?: (id: string) => void;
  onClick?: () => void;
  compact?: boolean;
}

const categoryIcons: Record<NotificationCategory, React.ComponentType<{ className?: string }>> = {
  general: Bell,
  workflow: FileText,
  approval: CheckCircle,
  alert: AlertTriangle,
  reminder: Clock,
  system: Settings,
};

const priorityColors: Record<NotificationPriority, string> = {
  low: 'bg-gray-100',
  normal: 'bg-blue-100',
  high: 'bg-orange-100',
  urgent: 'bg-red-100',
};

const priorityBorders: Record<NotificationPriority, string> = {
  low: 'border-l-gray-400',
  normal: 'border-l-blue-400',
  high: 'border-l-orange-400',
  urgent: 'border-l-red-400',
};

export function NotificationItem({
  notification,
  onMarkRead,
  onClick,
  compact = false,
}: NotificationItemProps) {
  const CategoryIcon = categoryIcons[notification.category] || Bell;
  const isUnread = notification.status !== 'read';

  const handleClick = () => {
    if (isUnread && onMarkRead) {
      onMarkRead(notification.id);
    }
    onClick?.();
  };

  const content = (
    <div
      className={cn(
        'flex items-start gap-3 p-3 border-l-4 transition-colors cursor-pointer',
        priorityBorders[notification.priority],
        isUnread ? 'bg-blue-50/50' : 'bg-white',
        'hover:bg-gray-50'
      )}
      onClick={notification.action_url ? undefined : handleClick}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex-shrink-0 rounded-full p-2',
          priorityColors[notification.priority]
        )}
      >
        <CategoryIcon className="h-4 w-4 text-gray-700" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p
            className={cn(
              'text-sm',
              isUnread ? 'font-semibold text-gray-900' : 'font-medium text-gray-700'
            )}
          >
            {notification.title}
          </p>
          {isUnread && (
            <span className="flex-shrink-0 h-2 w-2 rounded-full bg-blue-500" />
          )}
        </div>

        {!compact && (
          <p className="mt-1 text-sm text-gray-600 line-clamp-2">
            {notification.message}
          </p>
        )}

        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
          <span>
            {formatDistanceToNow(new Date(notification.created_at), {
              addSuffix: true,
            })}
          </span>
          {notification.priority !== 'normal' && (
            <>
              <span>·</span>
              <span
                className={cn(
                  'capitalize',
                  notification.priority === 'urgent' && 'text-red-600 font-medium',
                  notification.priority === 'high' && 'text-orange-600 font-medium'
                )}
              >
                {notification.priority}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );

  if (notification.action_url) {
    return (
      <Link href={notification.action_url} onClick={handleClick}>
        {content}
      </Link>
    );
  }

  return content;
}
