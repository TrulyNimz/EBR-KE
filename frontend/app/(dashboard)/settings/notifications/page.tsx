/**
 * Notification preferences settings page.
 */
import { Metadata } from 'next';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { NotificationPreferencesForm } from '@/components/notifications';

export const metadata: Metadata = {
  title: 'Notification Settings | EBR System',
  description: 'Manage your notification preferences',
};

export default function NotificationSettingsPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          href="/settings"
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Settings
        </Link>
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Notification Preferences
        </h1>
        <p className="text-gray-600 mt-1">
          Control how and when you receive notifications
        </p>
      </div>

      {/* Form */}
      <NotificationPreferencesForm />
    </div>
  );
}
