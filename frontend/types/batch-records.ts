/**
 * Batch Records TypeScript types.
 * Field names match the Django REST Framework serializer output exactly.
 */

export type BatchStatus =
  | 'draft'
  | 'in_progress'
  | 'pending_review'
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'completed'
  | 'cancelled';

export type StepStatus = 'pending' | 'in_progress' | 'completed' | 'skipped' | 'failed';

export type StepType =
  | 'data_entry'
  | 'verification'
  | 'approval'
  | 'signature'
  | 'attachment'
  | 'calculation'
  | 'instruction';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
}

/**
 * BatchStep — matches BatchStepSerializer fields exactly.
 */
export interface BatchStep {
  id: string;
  code: string;
  name: string;
  description: string;
  instructions: string;
  sequence: number;
  step_type: StepType;
  status: StepStatus;
  form_schema: Record<string, unknown>;
  data: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  executed_by: string | null;
  executed_by_name: string | null;
  verified_by: string | null;
  verified_by_name: string | null;
  verified_at: string | null;
  has_deviation: boolean;
  deviation_notes: string;
  requires_signature: boolean;
  signature_meaning: string;
  can_start: boolean;
  created_at: string;
  modified_at: string;
}

/**
 * BatchAttachment — matches BatchAttachmentSerializer fields exactly.
 */
export interface BatchAttachment {
  id: string;
  batch: string;
  step: string | null;
  file: string;
  filename: string;
  file_size: number;
  content_type: string;
  attachment_type: string;
  title: string;
  description: string;
  version: number;
  file_hash: string;
  uploaded_by: string;
  created_at: string;
}

/**
 * BatchStepTemplate — matches BatchStepTemplateSerializer fields exactly.
 */
export interface BatchStepTemplate {
  id: string;
  code: string;
  name: string;
  description: string;
  instructions: string;
  sequence: number;
  step_type: StepType;
  form_schema: Record<string, unknown>;
  requires_verification: boolean;
  requires_signature: boolean;
  signature_meaning: string;
  required_role: string;
  verifier_role: string;
  workflow_state: string;
  default_data: Record<string, unknown>;
}

/**
 * BatchTemplate — matches BatchTemplateSerializer fields exactly.
 */
export interface BatchTemplate {
  id: string;
  code: string;
  name: string;
  description: string;
  version: number;
  status: string;
  product_code: string;
  product_name: string;
  workflow: string | null;
  module_type: string;
  default_quantity_unit: string;
  default_custom_data: Record<string, unknown>;
  step_templates: BatchStepTemplate[];
  created_by: string;
  created_by_name: string;
  created_at: string;
  modified_at: string;
}

/**
 * BatchListItem — matches BatchListSerializer fields exactly (lightweight list view).
 */
export interface BatchListItem {
  id: string;
  batch_number: string;
  name: string;
  product_code: string;
  product_name: string;
  status: BatchStatus;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  module_type: string;
  completion_percentage: number;
  step_count: number;
  scheduled_start: string | null;
  actual_start: string | null;
  created_by_name: string;
  created_at: string;
}

/**
 * Batch — matches BatchSerializer fields exactly (full detail view).
 * Steps are nested directly on the batch — no separate BatchRecord concept.
 */
export interface Batch {
  id: string;
  batch_number: string;
  name: string;
  description: string;
  product_code: string;
  product_name: string;
  template: string | null;
  status: BatchStatus;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  module_type: string;
  workflow_instance: string | null;
  scheduled_start: string | null;
  scheduled_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  planned_quantity: string;
  actual_quantity: string | null;
  quantity_unit: string;
  custom_data: Record<string, unknown>;
  completion_percentage: number;
  is_complete: boolean;
  integrity_valid: boolean;
  steps: BatchStep[];
  attachments: BatchAttachment[];
  created_by: string;
  created_by_name: string;
  modified_by: string | null;
  modified_by_name: string | null;
  created_at: string;
  modified_at: string;
  record_checksum: string;
  version: number;
}

// Request/Response types

export interface BatchListParams {
  page?: number;
  page_size?: number;
  status?: BatchStatus;
  search?: string;
  ordering?: string;
  product_code?: string;
  module_type?: string;
  created_after?: string;
  created_before?: string;
}

export interface BatchListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: BatchListItem[];
}

export interface CreateBatchRequest {
  batch_number: string;
  name: string;
  description?: string;
  product_code: string;
  product_name: string;
  template?: string;
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  module_type?: string;
  scheduled_start?: string;
  scheduled_end?: string;
  planned_quantity: number;
  quantity_unit: string;
  custom_data?: Record<string, unknown>;
}

export interface UpdateBatchRequest {
  name?: string;
  description?: string;
  product_name?: string;
  planned_quantity?: number;
  scheduled_start?: string;
  scheduled_end?: string;
  custom_data?: Record<string, unknown>;
}

export interface ExecuteStepRequest {
  data?: Record<string, unknown>;
  has_deviation?: boolean;
  deviation_notes?: string;
}

export interface CreateSignatureRequest {
  object_id: string;
  content_type: string;
  meaning: string;
  password: string;
  notes?: string;
}
