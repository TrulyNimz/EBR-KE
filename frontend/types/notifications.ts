/**
 * Notification types for the EBR system.
 */

export type NotificationChannel = 'in_app' | 'email' | 'push' | 'sms';
export type NotificationStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed';
export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent';
export type NotificationCategory =
  | 'general'
  | 'workflow'
  | 'approval'
  | 'alert'
  | 'reminder'
  | 'system';

export interface NotificationTemplate {
  id: string;
  code: string;
  name: string;
  description: string;
  channel: NotificationChannel;
  category: NotificationCategory;
  subject_template: string;
  body_template: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  recipient_id: string;
  template?: NotificationTemplate;
  channel: NotificationChannel;
  category: NotificationCategory;
  priority: NotificationPriority;
  status: NotificationStatus;
  title: string;
  message: string;
  action_url?: string;
  metadata: Record<string, unknown>;
  related_type?: string;
  related_id?: string;
  read_at?: string;
  sent_at?: string;
  delivered_at?: string;
  created_at: string;
  updated_at: string;
}

export interface NotificationPreferences {
  id: string;
  user_id: string;
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  in_app_enabled: boolean;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  category_preferences: Record<NotificationCategory, {
    email: boolean;
    push: boolean;
    sms: boolean;
    in_app: boolean;
  }>;
  digest_enabled: boolean;
  digest_frequency: 'daily' | 'weekly' | 'never';
  created_at: string;
  updated_at: string;
}

export interface DeviceToken {
  id: string;
  token: string;
  platform: 'ios' | 'android' | 'web';
  device_id?: string;
  device_name?: string;
  app_version?: string;
  is_active: boolean;
  last_used_at?: string;
  created_at: string;
}

export interface NotificationSummary {
  status_counts: Record<NotificationStatus, number>;
  unread_by_category: Record<NotificationCategory, number>;
  high_priority_unread: number;
  total: number;
}

export interface SendNotificationRequest {
  recipient_id?: string;
  recipient_ids?: string[];
  title?: string;
  message?: string;
  template_code?: string;
  context?: Record<string, unknown>;
  channel?: NotificationChannel;
  category?: NotificationCategory;
  priority?: NotificationPriority;
  action_url?: string;
  metadata?: Record<string, unknown>;
  related_type?: string;
  related_id?: string;
  async?: boolean;
}

export interface MarkReadRequest {
  notification_ids?: string[];
  mark_all?: boolean;
}

export interface NotificationFilters {
  status?: NotificationStatus;
  channel?: NotificationChannel;
  category?: NotificationCategory;
  priority?: NotificationPriority;
}
