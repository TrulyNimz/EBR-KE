/**
 * IAM API — Users, Roles, Permissions.
 */
import { apiClient, type PaginatedResponse } from './client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UserListItem {
  id: string;
  email: string;
  employee_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  department: string;
  is_active: boolean;
  is_locked: boolean;
  mfa_enabled: boolean;
  last_login: string | null;
  created_at: string;
  roles: string[];
}

export interface UserDetail extends UserListItem {
  title: string;
  phone: string;
  digital_signature_enabled: boolean;
  permissions: string[];
}

export interface CreateUserPayload {
  email: string;
  employee_id: string;
  first_name: string;
  last_name: string;
  title?: string;
  department?: string;
  phone?: string;
  password: string;
  confirm_password: string;
}

export interface UpdateUserPayload {
  first_name?: string;
  last_name?: string;
  title?: string;
  department?: string;
  phone?: string;
  is_active?: boolean;
}

export interface Permission {
  id: string;
  code: string;
  name: string;
  description: string;
  module: string;
  resource: string;
  action: string;
  is_system: boolean;
}

export interface Role {
  id: string;
  name: string;
  code: string;
  description: string;
  parent_role: string | null;
  parent_role_name: string | null;
  permissions: Permission[];
  is_system_role: boolean;
  is_active: boolean;
  created_at: string;
}

export interface UserListParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  department?: string;
}

// ---------------------------------------------------------------------------
// User API
// ---------------------------------------------------------------------------

export function getUsers(params?: UserListParams): Promise<PaginatedResponse<UserListItem>> {
  return apiClient.get('/api/v1/users/', { params });
}

export function getUser(id: string): Promise<UserDetail> {
  return apiClient.get(`/api/v1/users/${id}/`);
}

export function createUser(data: CreateUserPayload): Promise<UserDetail> {
  return apiClient.post('/api/v1/users/', data);
}

export function updateUser(id: string, data: UpdateUserPayload): Promise<UserDetail> {
  return apiClient.patch(`/api/v1/users/${id}/`, data);
}

export function lockUser(id: string): Promise<void> {
  return apiClient.post(`/api/v1/users/${id}/lock/`);
}

export function unlockUser(id: string): Promise<void> {
  return apiClient.post(`/api/v1/users/${id}/unlock/`);
}

export function forcePasswordReset(id: string): Promise<void> {
  return apiClient.post(`/api/v1/users/${id}/reset_password/`);
}

// ---------------------------------------------------------------------------
// Role API
// ---------------------------------------------------------------------------

export function getRoles(): Promise<PaginatedResponse<Role>> {
  return apiClient.get('/api/v1/roles/');
}

export function getRole(id: string): Promise<Role> {
  return apiClient.get(`/api/v1/roles/${id}/`);
}

// ---------------------------------------------------------------------------
// User-Role API
// ---------------------------------------------------------------------------

export function assignRole(userId: string, roleId: string, reason?: string) {
  return apiClient.post('/api/v1/user-roles/', { user: userId, role: roleId, reason });
}

export function revokeRole(userRoleId: string) {
  return apiClient.delete(`/api/v1/user-roles/${userRoleId}/`);
}
