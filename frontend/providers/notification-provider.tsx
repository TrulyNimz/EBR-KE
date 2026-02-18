/**
 * Notification provider component.
 * Initializes real-time notification connection and renders toast container.
 */
'use client';

import { useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useNotificationStore } from '@/stores/notification-store';
import { ToastContainer } from '@/components/notifications';

interface NotificationProviderProps {
  children: React.ReactNode;
}

export function NotificationProvider({ children }: NotificationProviderProps) {
  const { data: session, status } = useSession();
  const { connectSSE, disconnectSSE, fetchUnreadCount, reset } = useNotificationStore();

  useEffect(() => {
    if (status === 'authenticated' && session?.user) {
      // Fetch initial unread count
      fetchUnreadCount();

      // Connect to SSE for real-time notifications
      connectSSE();
    } else if (status === 'unauthenticated') {
      // Reset notification state on logout
      reset();
    }

    return () => {
      disconnectSSE();
    };
  }, [status, session, connectSSE, disconnectSSE, fetchUnreadCount, reset]);

  return (
    <>
      {children}
      <ToastContainer />
    </>
  );
}
