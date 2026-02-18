/**
 * Notification preferences form component.
 */
'use client';

import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Bell,
  Mail,
  Smartphone,
  MessageSquare,
  Moon,
  Clock,
  Loader2,
} from 'lucide-react';
import { useNotificationStore } from '@/stores/notification-store';
import { NotificationCategory, NotificationPreferences } from '@/types/notifications';
import { cn } from '@/lib/utils';

const preferencesSchema = z.object({
  email_enabled: z.boolean(),
  push_enabled: z.boolean(),
  sms_enabled: z.boolean(),
  in_app_enabled: z.boolean(),
  quiet_hours_enabled: z.boolean(),
  quiet_hours_start: z.string().optional(),
  quiet_hours_end: z.string().optional(),
  digest_enabled: z.boolean(),
  digest_frequency: z.enum(['daily', 'weekly', 'never']),
  category_preferences: z.record(z.object({
    email: z.boolean(),
    push: z.boolean(),
    sms: z.boolean(),
    in_app: z.boolean(),
  })),
});

type PreferencesFormData = z.infer<typeof preferencesSchema>;

const categoryLabels: Record<NotificationCategory, { label: string; description: string }> = {
  general: {
    label: 'General',
    description: 'General announcements and updates',
  },
  workflow: {
    label: 'Workflow',
    description: 'Status updates on batch records and processes',
  },
  approval: {
    label: 'Approvals',
    description: 'Approval requests and decisions',
  },
  alert: {
    label: 'Alerts',
    description: 'Important alerts requiring attention',
  },
  reminder: {
    label: 'Reminders',
    description: 'Task reminders and follow-ups',
  },
  system: {
    label: 'System',
    description: 'System maintenance and security updates',
  },
};

export function NotificationPreferencesForm() {
  const {
    preferences,
    preferencesLoading,
    fetchPreferences,
    updatePreferences,
  } = useNotificationStore();

  const form = useForm<PreferencesFormData>({
    resolver: zodResolver(preferencesSchema),
    defaultValues: {
      email_enabled: true,
      push_enabled: true,
      sms_enabled: false,
      in_app_enabled: true,
      quiet_hours_enabled: false,
      quiet_hours_start: '22:00',
      quiet_hours_end: '07:00',
      digest_enabled: false,
      digest_frequency: 'daily',
      category_preferences: {},
    },
  });

  // Fetch preferences on mount
  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  // Update form when preferences load
  useEffect(() => {
    if (preferences) {
      form.reset({
        email_enabled: preferences.email_enabled,
        push_enabled: preferences.push_enabled,
        sms_enabled: preferences.sms_enabled,
        in_app_enabled: preferences.in_app_enabled,
        quiet_hours_enabled: preferences.quiet_hours_enabled,
        quiet_hours_start: preferences.quiet_hours_start || '22:00',
        quiet_hours_end: preferences.quiet_hours_end || '07:00',
        digest_enabled: preferences.digest_enabled,
        digest_frequency: preferences.digest_frequency,
        category_preferences: preferences.category_preferences,
      });
    }
  }, [preferences, form]);

  const onSubmit = (data: PreferencesFormData) => {
    updatePreferences(data);
  };

  const watchQuietHours = form.watch('quiet_hours_enabled');
  const watchDigest = form.watch('digest_enabled');

  if (preferencesLoading && !preferences) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
      {/* Channel Preferences */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Notification Channels
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          Choose how you want to receive notifications
        </p>

        <div className="space-y-4">
          {/* In-App */}
          <label className="flex items-center justify-between p-4 bg-white rounded-lg border cursor-pointer hover:bg-gray-50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Bell className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">In-App Notifications</p>
                <p className="text-sm text-gray-500">
                  Show notifications within the application
                </p>
              </div>
            </div>
            <Controller
              name="in_app_enabled"
              control={form.control}
              render={({ field }) => (
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={field.onChange}
                  className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              )}
            />
          </label>

          {/* Email */}
          <label className="flex items-center justify-between p-4 bg-white rounded-lg border cursor-pointer hover:bg-gray-50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Mail className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Email Notifications</p>
                <p className="text-sm text-gray-500">
                  Receive important updates via email
                </p>
              </div>
            </div>
            <Controller
              name="email_enabled"
              control={form.control}
              render={({ field }) => (
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={field.onChange}
                  className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              )}
            />
          </label>

          {/* Push */}
          <label className="flex items-center justify-between p-4 bg-white rounded-lg border cursor-pointer hover:bg-gray-50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Smartphone className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Push Notifications</p>
                <p className="text-sm text-gray-500">
                  Get instant alerts on your mobile device
                </p>
              </div>
            </div>
            <Controller
              name="push_enabled"
              control={form.control}
              render={({ field }) => (
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={field.onChange}
                  className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              )}
            />
          </label>

          {/* SMS */}
          <label className="flex items-center justify-between p-4 bg-white rounded-lg border cursor-pointer hover:bg-gray-50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <MessageSquare className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">SMS Notifications</p>
                <p className="text-sm text-gray-500">
                  Receive critical alerts via text message
                </p>
              </div>
            </div>
            <Controller
              name="sms_enabled"
              control={form.control}
              render={({ field }) => (
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={field.onChange}
                  className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              )}
            />
          </label>
        </div>
      </section>

      {/* Quiet Hours */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quiet Hours</h2>
        <p className="text-sm text-gray-600 mb-4">
          Pause non-urgent notifications during specific hours
        </p>

        <div className="bg-white rounded-lg border p-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-100 rounded-lg">
                <Moon className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Enable Quiet Hours</p>
                <p className="text-sm text-gray-500">
                  Only urgent notifications will be sent during quiet hours
                </p>
              </div>
            </div>
            <Controller
              name="quiet_hours_enabled"
              control={form.control}
              render={({ field }) => (
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={field.onChange}
                  className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              )}
            />
          </label>

          {watchQuietHours && (
            <div className="mt-4 pt-4 border-t flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">From</label>
                <Controller
                  name="quiet_hours_start"
                  control={form.control}
                  render={({ field }) => (
                    <input
                      type="time"
                      value={field.value}
                      onChange={field.onChange}
                      className="px-3 py-1.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  )}
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">To</label>
                <Controller
                  name="quiet_hours_end"
                  control={form.control}
                  render={({ field }) => (
                    <input
                      type="time"
                      value={field.value}
                      onChange={field.onChange}
                      className="px-3 py-1.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  )}
                />
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Email Digest */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Email Digest</h2>
        <p className="text-sm text-gray-600 mb-4">
          Get a summary of notifications instead of individual emails
        </p>

        <div className="bg-white rounded-lg border p-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-teal-100 rounded-lg">
                <Clock className="h-5 w-5 text-teal-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Enable Email Digest</p>
                <p className="text-sm text-gray-500">
                  Receive a periodic summary of your notifications
                </p>
              </div>
            </div>
            <Controller
              name="digest_enabled"
              control={form.control}
              render={({ field }) => (
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={field.onChange}
                  className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              )}
            />
          </label>

          {watchDigest && (
            <div className="mt-4 pt-4 border-t">
              <label className="text-sm text-gray-600 mb-2 block">Frequency</label>
              <Controller
                name="digest_frequency"
                control={form.control}
                render={({ field }) => (
                  <select
                    value={field.value}
                    onChange={field.onChange}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                  </select>
                )}
              />
            </div>
          )}
        </div>
      </section>

      {/* Category Preferences */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Category Preferences
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          Customize notification delivery for each category
        </p>

        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                  Category
                </th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">
                  In-App
                </th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">
                  Email
                </th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">
                  Push
                </th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">
                  SMS
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(Object.keys(categoryLabels) as NotificationCategory[]).map((category) => (
                <tr key={category} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">
                      {categoryLabels[category].label}
                    </p>
                    <p className="text-xs text-gray-500">
                      {categoryLabels[category].description}
                    </p>
                  </td>
                  {(['in_app', 'email', 'push', 'sms'] as const).map((channel) => (
                    <td key={channel} className="px-4 py-3 text-center">
                      <Controller
                        name={`category_preferences.${category}.${channel}`}
                        control={form.control}
                        defaultValue={true}
                        render={({ field }) => (
                          <input
                            type="checkbox"
                            checked={field.value ?? true}
                            onChange={field.onChange}
                            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                        )}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Submit */}
      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={() => form.reset()}
          className="px-4 py-2 text-gray-700 bg-white border rounded-lg hover:bg-gray-50 transition-colors"
        >
          Reset
        </button>
        <button
          type="submit"
          disabled={preferencesLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors inline-flex items-center gap-2"
        >
          {preferencesLoading && <Loader2 className="h-4 w-4 animate-spin" />}
          Save Preferences
        </button>
      </div>
    </form>
  );
}
