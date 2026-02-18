/**
 * Notifications page.
 */
import { Metadata } from 'next';
import { NotificationCenter } from '@/components/notifications';

export const metadata: Metadata = {
  title: 'Notifications | EBR System',
  description: 'View and manage your notifications',
};

export default function NotificationsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <NotificationCenter />
    </div>
  );
}
