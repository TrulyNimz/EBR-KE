/**
 * Custom hook for toast notifications.
 */
import { useNotificationStore } from '@/stores/notification-store';

interface ToastOptions {
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function useToast() {
  const { addToast, removeToast, clearToasts } = useNotificationStore();

  const toast = {
    success: (options: ToastOptions) => {
      addToast({ ...options, type: 'success' });
    },
    error: (options: ToastOptions) => {
      addToast({ ...options, type: 'error' });
    },
    warning: (options: ToastOptions) => {
      addToast({ ...options, type: 'warning' });
    },
    info: (options: ToastOptions) => {
      addToast({ ...options, type: 'info' });
    },
    dismiss: removeToast,
    dismissAll: clearToasts,
  };

  return toast;
}
