/**
 * Batch Records API client functions.
 * URLs match the Django REST Framework router registration exactly:
 *   router.register('batches', BatchViewSet)
 *   batch_router.register('steps', BatchStepViewSet)     → /batches/{id}/steps/
 *   batch_router.register('attachments', ...)             → /batches/{id}/attachments/
 */
import { apiClient } from './client';
import type {
  Batch,
  BatchListItem,
  BatchStep,
  BatchAttachment,
  BatchTemplate,
  BatchListParams,
  BatchListResponse,
  CreateBatchRequest,
  UpdateBatchRequest,
  ExecuteStepRequest,
  CreateSignatureRequest,
} from '@/types/batch-records';

const BASE = '/api/v1';

// ---------------------------------------------------------------------------
// Batches
// ---------------------------------------------------------------------------

export async function getBatches(params?: BatchListParams): Promise<BatchListResponse> {
  const response = await apiClient.get<BatchListResponse>(`${BASE}/batches/`, { params });
  return response.data;
}

export async function getBatch(id: string): Promise<Batch> {
  const response = await apiClient.get<Batch>(`${BASE}/batches/${id}/`);
  return response.data;
}

export async function createBatch(data: CreateBatchRequest): Promise<Batch> {
  const response = await apiClient.post<Batch>(`${BASE}/batches/`, data);
  return response.data;
}

export async function updateBatch(id: string, data: UpdateBatchRequest): Promise<Batch> {
  const response = await apiClient.patch<Batch>(`${BASE}/batches/${id}/`, data);
  return response.data;
}

export async function startBatch(id: string): Promise<Batch> {
  const response = await apiClient.post<Batch>(`${BASE}/batches/${id}/start/`);
  return response.data;
}

export async function completeBatch(id: string): Promise<Batch> {
  const response = await apiClient.post<Batch>(`${BASE}/batches/${id}/complete/`);
  return response.data;
}

// ---------------------------------------------------------------------------
// Batch Steps  (nested under /batches/{batchId}/steps/)
// ---------------------------------------------------------------------------

export async function getBatchSteps(batchId: string): Promise<BatchStep[]> {
  const response = await apiClient.get<BatchStep[]>(`${BASE}/batches/${batchId}/steps/`);
  return response.data;
}

export async function startStep(batchId: string, stepId: string): Promise<BatchStep> {
  const response = await apiClient.post<BatchStep>(
    `${BASE}/batches/${batchId}/steps/${stepId}/start/`
  );
  return response.data;
}

/**
 * Execute (complete) a batch step with form data.
 * Maps to BatchStepViewSet.complete() action on the backend.
 */
export async function executeStep(
  batchId: string,
  stepId: string,
  data: ExecuteStepRequest
): Promise<BatchStep> {
  const response = await apiClient.post<BatchStep>(
    `${BASE}/batches/${batchId}/steps/${stepId}/complete/`,
    data
  );
  return response.data;
}

export async function verifyStep(batchId: string, stepId: string): Promise<BatchStep> {
  const response = await apiClient.post<BatchStep>(
    `${BASE}/batches/${batchId}/steps/${stepId}/verify/`
  );
  return response.data;
}

// ---------------------------------------------------------------------------
// Digital Signatures  (audit app — /audit/signatures/)
// ---------------------------------------------------------------------------

/**
 * Apply a digital signature to any object (step, batch, etc.).
 * The audit app's DigitalSignatureViewSet handles creation.
 */
export async function createSignature(data: CreateSignatureRequest): Promise<unknown> {
  const response = await apiClient.post(`${BASE}/audit/signatures/`, data);
  return response.data;
}

/**
 * Sign a batch step. Sends to the audit signatures endpoint with the
 * correct content type for BatchStep.
 */
export async function signStep(
  stepId: string,
  password: string,
  meaning: string
): Promise<unknown> {
  return createSignature({
    object_id: stepId,
    content_type: 'batch_records.batchstep',
    meaning,
    password,
  });
}

// ---------------------------------------------------------------------------
// Batch Attachments  (nested under /batches/{batchId}/attachments/)
// ---------------------------------------------------------------------------

export async function getAttachments(batchId: string): Promise<BatchAttachment[]> {
  const response = await apiClient.get<BatchAttachment[]>(
    `${BASE}/batches/${batchId}/attachments/`
  );
  return response.data;
}

export async function uploadAttachment(
  batchId: string,
  file: File,
  metadata?: { title?: string; description?: string; attachment_type?: string }
): Promise<BatchAttachment> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('filename', file.name);
  if (metadata?.title) formData.append('title', metadata.title);
  if (metadata?.description) formData.append('description', metadata.description);
  if (metadata?.attachment_type) formData.append('attachment_type', metadata.attachment_type);

  const response = await apiClient.post<BatchAttachment>(
    `${BASE}/batches/${batchId}/attachments/`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return response.data;
}

export async function deleteAttachment(batchId: string, attachmentId: string): Promise<void> {
  await apiClient.delete(`${BASE}/batches/${batchId}/attachments/${attachmentId}/`);
}

// ---------------------------------------------------------------------------
// Batch Templates
// ---------------------------------------------------------------------------

export async function getBatchTemplates(): Promise<BatchTemplate[]> {
  const response = await apiClient.get<BatchTemplate[]>(`${BASE}/templates/`);
  return response.data;
}

export async function getBatchTemplate(id: string): Promise<BatchTemplate> {
  const response = await apiClient.get<BatchTemplate>(`${BASE}/templates/${id}/`);
  return response.data;
}
