/**
 * Workflow API — definitions, instances, approvals.
 */
import { apiClient, type PaginatedResponse } from './client';

// ---------------------------------------------------------------------------
// Types — Workflow Definitions
// ---------------------------------------------------------------------------

export interface WorkflowState {
  id: string;
  code: string;
  name: string;
  description: string;
  state_type: string;
  is_initial: boolean;
  is_terminal: boolean;
  color: string;
  order: number;
  required_actions: string[];
  required_signatures: number;
}

export interface WorkflowTransition {
  id: string;
  code: string;
  name: string;
  description: string;
  from_state: string;
  from_state_name: string;
  to_state: string;
  to_state_name: string;
  transition_type: string;
  requires_approval: boolean;
  required_permission: string;
  required_roles: string[];
  button_label: string;
  button_color: string;
  is_active: boolean;
  order: number;
}

export interface WorkflowDefinition {
  id: string;
  code: string;
  name: string;
  description: string;
  version: number;
  status: 'draft' | 'active' | 'deprecated' | 'archived';
  applicable_record_types: string[];
  states: WorkflowState[];
  transitions: WorkflowTransition[];
  created_by: string;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowListItem {
  id: string;
  code: string;
  name: string;
  version: number;
  status: 'draft' | 'active' | 'deprecated' | 'archived';
  applicable_record_types: string[];
  state_count: number;
  transition_count: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Types — Instances & Approvals
// ---------------------------------------------------------------------------

export interface WorkflowInstance {
  id: string;
  workflow: string;
  workflow_name: string;
  current_state: string;
  current_state_name: string;
  current_state_color: string;
  status: string;
  object_id: string;
  started_at: string;
  completed_at: string | null;
  state_entered_at: string;
  state_deadline: string | null;
  pending_approvals: PendingApproval[];
  available_transitions: AvailableTransition[];
}

export interface PendingApproval {
  id: string;
  transition_name: string;
  status: string;
  requested_by_name: string;
  requested_at: string;
}

export interface AvailableTransition {
  id: string;
  name: string;
  button_label: string;
  button_color: string;
  can_execute: boolean;
  reason: string | null;
}

export interface ApprovalRequest {
  id: string;
  transition_name: string;
  status: string;
  requested_by_name: string;
  requested_at: string;
  deadline: string | null;
  request_notes: string;
}

// ---------------------------------------------------------------------------
// Workflow Definition API
// ---------------------------------------------------------------------------

export function getWorkflows(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  search?: string;
}): Promise<PaginatedResponse<WorkflowListItem>> {
  return apiClient.get('/api/v1/workflows/definitions/', { params });
}

export function getWorkflow(id: string): Promise<WorkflowDefinition> {
  return apiClient.get(`/api/v1/workflows/definitions/${id}/`);
}

export function activateWorkflow(id: string): Promise<WorkflowDefinition> {
  return apiClient.post(`/api/v1/workflows/definitions/${id}/activate/`);
}

export function deprecateWorkflow(id: string): Promise<WorkflowDefinition> {
  return apiClient.post(`/api/v1/workflows/definitions/${id}/deprecate/`);
}

// ---------------------------------------------------------------------------
// Workflow Instance API
// ---------------------------------------------------------------------------

export function getWorkflowInstances(params?: {
  page?: number;
  status?: string;
}): Promise<PaginatedResponse<WorkflowInstance>> {
  return apiClient.get('/api/v1/workflows/instances/', { params });
}

export function getWorkflowInstance(id: string): Promise<WorkflowInstance> {
  return apiClient.get(`/api/v1/workflows/instances/${id}/`);
}

export function executeTransition(
  instanceId: string,
  transitionId: string,
  notes?: string
): Promise<WorkflowInstance> {
  return apiClient.post(`/api/v1/workflows/instances/${instanceId}/transition/`, {
    transition: transitionId,
    notes,
  });
}

// ---------------------------------------------------------------------------
// Approval API
// ---------------------------------------------------------------------------

export function getPendingApprovals(): Promise<PaginatedResponse<ApprovalRequest>> {
  return apiClient.get('/api/v1/workflows/approval-requests/pending/');
}

export function decideApproval(
  id: string,
  decision: 'approved' | 'rejected',
  comments?: string
): Promise<void> {
  return apiClient.post(`/api/v1/workflows/approval-requests/${id}/decide/`, { decision, comments });
}
