/**
 * Toast container component - renders all active toasts.
 */
'use client';

import { useNotificationStore } from '@/stores/notification-store';
import { Toast } from './toast';

export function ToastContainer() {
  const { toasts, removeToast } = useNotificationStore();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-label="Notifications"
      className="pointer-events-none fixed bottom-0 right-0 z-50 flex flex-col gap-2 p-4 sm:p-6 max-h-screen overflow-hidden"
    >
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          id={toast.id}
          title={toast.title}
          message={toast.message}
          type={toast.type}
          action={toast.action}
          onDismiss={removeToast}
        />
      ))}
    </div>
  );
}
