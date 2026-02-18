/**
 * Notification API client.
 */
import { apiClient, PaginatedResponse } from './client';
import {
  Notification,
  NotificationPreferences,
  NotificationSummary,
  NotificationFilters,
  MarkReadRequest,
  SendNotificationRequest,
  DeviceToken,
} from '@/types/notifications';

const BASE_URL = '/api/v1/notifications';

/**
 * Fetch notifications for the current user.
 */
export async function getNotifications(
  params?: NotificationFilters & { page?: number; page_size?: number }
): Promise<PaginatedResponse<Notification>> {
  const searchParams = new URLSearchParams();

  if (params?.status) searchParams.set('status', params.status);
  if (params?.channel) searchParams.set('channel', params.channel);
  if (params?.category) searchParams.set('category', params.category);
  if (params?.priority) searchParams.set('priority', params.priority);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));

  const query = searchParams.toString();
  return apiClient.get<PaginatedResponse<Notification>>(
    `${BASE_URL}/${query ? `?${query}` : ''}`
  );
}

/**
 * Get a single notification by ID.
 */
export async function getNotification(id: string): Promise<Notification> {
  return apiClient.get<Notification>(`${BASE_URL}/${id}/`);
}

/**
 * Mark notifications as read.
 */
export async function markNotificationsRead(
  data: MarkReadRequest
): Promise<{ message: string; count: number }> {
  return apiClient.post<{ message: string; count: number }>(
    `${BASE_URL}/mark-read/`,
    data
  );
}

/**
 * Mark a single notification as read.
 */
export async function markNotificationRead(id: string): Promise<Notification> {
  return apiClient.post<Notification>(`${BASE_URL}/${id}/read/`);
}

/**
 * Get unread notification count.
 */
export async function getUnreadCount(): Promise<{ unread_count: number }> {
  return apiClient.get<{ unread_count: number }>(`${BASE_URL}/unread-count/`);
}

/**
 * Get notification summary.
 */
export async function getNotificationSummary(): Promise<NotificationSummary> {
  return apiClient.get<NotificationSummary>(`${BASE_URL}/summary/`);
}

/**
 * Get user notification preferences.
 */
export async function getPreferences(): Promise<NotificationPreferences> {
  return apiClient.get<NotificationPreferences>(`${BASE_URL}/preferences/`);
}

/**
 * Update user notification preferences.
 */
export async function updatePreferences(
  data: Partial<NotificationPreferences>
): Promise<NotificationPreferences> {
  return apiClient.put<NotificationPreferences>(`${BASE_URL}/preferences/`, data);
}

/**
 * Partially update user notification preferences.
 */
export async function patchPreferences(
  data: Partial<NotificationPreferences>
): Promise<NotificationPreferences> {
  return apiClient.patch<NotificationPreferences>(`${BASE_URL}/preferences/`, data);
}

/**
 * Send a notification (admin only).
 */
export async function sendNotification(
  data: SendNotificationRequest
): Promise<{ message: string; notifications: Array<{ recipient_id: string; status: string }> }> {
  return apiClient.post(`${BASE_URL}/send/`, data);
}

/**
 * Register a device token for push notifications.
 */
export async function registerDeviceToken(data: {
  token: string;
  platform: 'ios' | 'android' | 'web';
  device_id?: string;
  device_name?: string;
  app_version?: string;
}): Promise<DeviceToken> {
  return apiClient.post<DeviceToken>(`${BASE_URL}/devices/register/`, data);
}

/**
 * Unregister a device token.
 */
export async function unregisterDeviceToken(
  token: string
): Promise<{ message: string }> {
  return apiClient.post<{ message: string }>(`${BASE_URL}/devices/unregister/`, {
    token,
  });
}

/**
 * Get user's registered device tokens.
 */
export async function getDeviceTokens(): Promise<PaginatedResponse<DeviceToken>> {
  return apiClient.get<PaginatedResponse<DeviceToken>>(`${BASE_URL}/devices/`);
}

/**
 * Create SSE connection for real-time notifications.
 */
export function createNotificationStream(
  onMessage: (notifications: Notification[]) => void,
  onError?: (error: Event) => void
): EventSource | null {
  if (typeof window === 'undefined') return null;

  const token = localStorage.getItem('access_token');
  if (!token) return null;

  // Note: SSE with auth typically requires URL-based token or cookie auth
  const eventSource = new EventSource(`${BASE_URL}/stream/`, {
    withCredentials: true,
  });

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (Array.isArray(data) && data.length > 0) {
        onMessage(data);
      }
    } catch {
      // Heartbeat or malformed data
    }
  };

  eventSource.onerror = (error) => {
    onError?.(error);
  };

  return eventSource;
}
