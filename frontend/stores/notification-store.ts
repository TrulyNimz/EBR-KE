/**
 * Zustand store for notification state management.
 */
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import {
  Notification,
  NotificationPreferences,
  NotificationSummary,
} from '@/types/notifications';
import * as notificationApi from '@/lib/api/notifications';

interface Toast {
  id: string;
  title: string;
  message?: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface NotificationState {
  // Notifications
  notifications: Notification[];
  unreadCount: number;
  summary: NotificationSummary | null;
  isLoading: boolean;
  error: string | null;

  // Preferences
  preferences: NotificationPreferences | null;
  preferencesLoading: boolean;

  // Toast notifications
  toasts: Toast[];

  // SSE connection
  eventSource: EventSource | null;

  // Actions
  fetchNotifications: (page?: number) => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  fetchSummary: () => Promise<void>;
  markAsRead: (ids: string[]) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  markSingleAsRead: (id: string) => Promise<void>;
  addNotification: (notification: Notification) => void;

  // Preferences actions
  fetchPreferences: () => Promise<void>;
  updatePreferences: (data: Partial<NotificationPreferences>) => Promise<void>;

  // Toast actions
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;

  // SSE actions
  connectSSE: () => void;
  disconnectSSE: () => void;

  // Reset
  reset: () => void;
}

const initialState = {
  notifications: [],
  unreadCount: 0,
  summary: null,
  isLoading: false,
  error: null,
  preferences: null,
  preferencesLoading: false,
  toasts: [],
  eventSource: null,
};

export const useNotificationStore = create<NotificationState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        fetchNotifications: async (page = 1) => {
          set({ isLoading: true, error: null });
          try {
            const response = await notificationApi.getNotifications({
              page,
              page_size: 20,
            });
            set({
              notifications:
                page === 1
                  ? response.results
                  : [...get().notifications, ...response.results],
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch notifications',
              isLoading: false,
            });
          }
        },

        fetchUnreadCount: async () => {
          try {
            const response = await notificationApi.getUnreadCount();
            set({ unreadCount: response.unread_count });
          } catch {
            // Silent fail for count
          }
        },

        fetchSummary: async () => {
          try {
            const summary = await notificationApi.getNotificationSummary();
            set({ summary });
          } catch {
            // Silent fail for summary
          }
        },

        markAsRead: async (ids: string[]) => {
          try {
            await notificationApi.markNotificationsRead({ notification_ids: ids });
            set((state) => ({
              notifications: state.notifications.map((n) =>
                ids.includes(n.id)
                  ? { ...n, status: 'read' as const, read_at: new Date().toISOString() }
                  : n
              ),
              unreadCount: Math.max(0, state.unreadCount - ids.length),
            }));
          } catch (error) {
            get().addToast({
              title: 'Error',
              message: 'Failed to mark notifications as read',
              type: 'error',
            });
          }
        },

        markAllAsRead: async () => {
          try {
            const response = await notificationApi.markNotificationsRead({ mark_all: true });
            set((state) => ({
              notifications: state.notifications.map((n) => ({
                ...n,
                status: 'read' as const,
                read_at: new Date().toISOString(),
              })),
              unreadCount: 0,
            }));
            get().addToast({
              title: 'Success',
              message: `${response.count} notifications marked as read`,
              type: 'success',
            });
          } catch {
            get().addToast({
              title: 'Error',
              message: 'Failed to mark all as read',
              type: 'error',
            });
          }
        },

        markSingleAsRead: async (id: string) => {
          try {
            const updated = await notificationApi.markNotificationRead(id);
            set((state) => ({
              notifications: state.notifications.map((n) =>
                n.id === id ? updated : n
              ),
              unreadCount: Math.max(0, state.unreadCount - 1),
            }));
          } catch {
            // Silent fail
          }
        },

        addNotification: (notification: Notification) => {
          set((state) => ({
            notifications: [notification, ...state.notifications],
            unreadCount: state.unreadCount + 1,
          }));

          // Show toast for high priority notifications
          if (notification.priority === 'high' || notification.priority === 'urgent') {
            get().addToast({
              title: notification.title,
              message: notification.message,
              type: notification.priority === 'urgent' ? 'warning' : 'info',
              duration: 8000,
              action: notification.action_url
                ? {
                    label: 'View',
                    onClick: () => {
                      window.location.href = notification.action_url!;
                    },
                  }
                : undefined,
            });
          }
        },

        fetchPreferences: async () => {
          set({ preferencesLoading: true });
          try {
            const preferences = await notificationApi.getPreferences();
            set({ preferences, preferencesLoading: false });
          } catch {
            set({ preferencesLoading: false });
          }
        },

        updatePreferences: async (data: Partial<NotificationPreferences>) => {
          set({ preferencesLoading: true });
          try {
            const preferences = await notificationApi.patchPreferences(data);
            set({ preferences, preferencesLoading: false });
            get().addToast({
              title: 'Preferences Updated',
              message: 'Your notification preferences have been saved',
              type: 'success',
            });
          } catch {
            set({ preferencesLoading: false });
            get().addToast({
              title: 'Error',
              message: 'Failed to update preferences',
              type: 'error',
            });
          }
        },

        addToast: (toast: Omit<Toast, 'id'>) => {
          const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
          const newToast = { ...toast, id };

          set((state) => ({
            toasts: [...state.toasts, newToast],
          }));

          // Auto-remove after duration
          const duration = toast.duration ?? 5000;
          if (duration > 0) {
            setTimeout(() => {
              get().removeToast(id);
            }, duration);
          }
        },

        removeToast: (id: string) => {
          set((state) => ({
            toasts: state.toasts.filter((t) => t.id !== id),
          }));
        },

        clearToasts: () => {
          set({ toasts: [] });
        },

        connectSSE: () => {
          const { eventSource } = get();
          if (eventSource) return;

          const source = notificationApi.createNotificationStream(
            (notifications) => {
              notifications.forEach((n) => get().addNotification(n));
            },
            (error) => {
              console.error('SSE connection error:', error);
              // Attempt reconnect after 5 seconds
              setTimeout(() => {
                get().disconnectSSE();
                get().connectSSE();
              }, 5000);
            }
          );

          set({ eventSource: source });
        },

        disconnectSSE: () => {
          const { eventSource } = get();
          if (eventSource) {
            eventSource.close();
            set({ eventSource: null });
          }
        },

        reset: () => {
          get().disconnectSSE();
          set(initialState);
        },
      }),
      {
        name: 'notification-storage',
        partialize: (state) => ({
          // Only persist preferences
          preferences: state.preferences,
        }),
      }
    ),
    { name: 'NotificationStore' }
  )
);
