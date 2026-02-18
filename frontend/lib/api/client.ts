/**
 * API client for the EBR frontend.
 */
import axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import { getSession, signOut } from 'next-auth/react';
import {
  isAPIErrorResponse,
  parseAPIError,
  NetworkError,
  TimeoutError,
  AuthenticationError,
  errorFromStatusCode,
} from '../errors';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * Paginated response interface.
 */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Axios client configured for the EBR API.
 * Includes interceptors for authentication and error handling.
 */
export const axiosClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token and request ID
axiosClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const session = await getSession();

    if (session?.accessToken) {
      config.headers.Authorization = `Bearer ${session.accessToken}`;
    }

    // Add request ID for tracing
    config.headers['X-Request-ID'] = generateRequestId();

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
axiosClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    // Handle network errors
    if (!error.response) {
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        throw new TimeoutError();
      }
      throw new NetworkError();
    }

    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Handle 401 errors - token expired
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Trigger NextAuth session update which will refresh the token
        const session = await getSession();

        if (session?.accessToken) {
          originalRequest.headers.Authorization = `Bearer ${session.accessToken}`;
          return axiosClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, sign out
        await signOut({ redirect: true, callbackUrl: '/login' });
        throw new AuthenticationError('Session expired. Please log in again.');
      }
    }

    // Parse API error response
    if (isAPIErrorResponse(error.response.data)) {
      throw parseAPIError(error.response.data);
    }

    // Fallback to status-code based error
    throw errorFromStatusCode(
      error.response.status,
      typeof error.response.data === 'string'
        ? error.response.data
        : (error.response.data as { message?: string })?.message
    );
  }
);

/**
 * Generate a unique request ID.
 */
function generateRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

/**
 * Typed API client wrapper with consistent error handling.
 */
export const apiClient = {
  /**
   * GET request.
   */
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosClient.get<T>(url, config);
    return response.data;
  },

  /**
   * POST request.
   */
  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosClient.post<T>(url, data, config);
    return response.data;
  },

  /**
   * PUT request.
   */
  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosClient.put<T>(url, data, config);
    return response.data;
  },

  /**
   * PATCH request.
   */
  async patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosClient.patch<T>(url, data, config);
    return response.data;
  },

  /**
   * DELETE request.
   */
  async delete<T = void>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await axiosClient.delete<T>(url, config);
    return response.data;
  },

  /**
   * Upload file(s) with multipart/form-data.
   */
  async upload<T>(
    url: string,
    formData: FormData,
    onProgress?: (progress: number) => void,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await axiosClient.post<T>(url, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config?.headers,
      },
      onUploadProgress: onProgress
        ? (event) => {
            if (event.total) {
              onProgress(Math.round((event.loaded * 100) / event.total));
            }
          }
        : undefined,
    });
    return response.data;
  },

  /**
   * Download a file.
   */
  async download(url: string, filename: string): Promise<void> {
    const response = await axiosClient.get(url, {
      responseType: 'blob',
    });

    // Create download link
    const downloadUrl = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },
};

/**
 * Server-side API client for use in Server Components.
 */
export function createServerApiClient(accessToken?: string) {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: DEFAULT_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
    },
  });

  return {
    async get<T>(url: string): Promise<T> {
      const response = await client.get<T>(url);
      return response.data;
    },

    async post<T>(url: string, data?: unknown): Promise<T> {
      const response = await client.post<T>(url, data);
      return response.data;
    },

    async put<T>(url: string, data?: unknown): Promise<T> {
      const response = await client.put<T>(url, data);
      return response.data;
    },

    async patch<T>(url: string, data?: unknown): Promise<T> {
      const response = await client.patch<T>(url, data);
      return response.data;
    },

    async delete<T = void>(url: string): Promise<T> {
      const response = await client.delete<T>(url);
      return response.data;
    },
  };
}

export default apiClient;
