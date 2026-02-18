/**
 * Healthcare module API — patients, medications, vital signs, clinical notes.
 */
import { apiClient, type PaginatedResponse } from './client';

// ---------------------------------------------------------------------------
// Types — Patients
// ---------------------------------------------------------------------------

export type PatientStatus = 'active' | 'discharged' | 'transferred' | 'deceased';
export type PatientGender = 'male' | 'female' | 'other' | 'unknown';

export interface Patient {
  id: string;
  patient_number: string;
  first_name: string;
  middle_name: string;
  last_name: string;
  full_name: string;
  date_of_birth: string;
  age: number;
  gender: PatientGender;
  blood_type: string;
  status: PatientStatus;
  ward: string;
  bed_number: string;
  admission_date: string | null;
  discharge_date: string | null;
  attending_physician: string | null;
  attending_physician_name: string | null;
  allergies_count: number;
  created_at: string;
}

export interface PatientAllergy {
  id: string;
  allergen: string;
  allergen_type: string;
  severity: 'mild' | 'moderate' | 'severe' | 'life_threatening';
  reaction: string;
  onset_date: string | null;
  verified: boolean;
  verified_by_name: string | null;
  notes: string;
}

export interface AdmitPatientPayload {
  ward: string;
  bed_number?: string;
  attending_physician?: string;
}

export interface CreatePatientPayload {
  patient_number: string;
  first_name: string;
  middle_name?: string;
  last_name: string;
  date_of_birth: string;
  gender: PatientGender;
  blood_type?: string;
  ward?: string;
}

// ---------------------------------------------------------------------------
// Types — Vital Signs
// ---------------------------------------------------------------------------

export interface VitalSigns {
  id: string;
  patient: string;
  temperature: number | null;
  temperature_method: string;
  systolic_bp: number | null;
  diastolic_bp: number | null;
  heart_rate: number | null;
  respiratory_rate: number | null;
  oxygen_saturation: number | null;
  pain_score: number | null;
  weight_kg: number | null;
  height_cm: number | null;
  bmi: number | null;
  gcs_total: number | null;
  blood_glucose: number | null;
  recorded_by_name: string;
  recorded_at: string;
  is_abnormal: boolean;
}

// ---------------------------------------------------------------------------
// Types — Clinical Notes
// ---------------------------------------------------------------------------

export interface ClinicalNote {
  id: string;
  patient: string;
  note_type: string;
  content: string;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  author_name: string;
  authored_at: string;
  is_final: boolean;
  requires_cosignature: boolean;
  cosigned_by_name: string | null;
}

// ---------------------------------------------------------------------------
// Types — Medication Orders
// ---------------------------------------------------------------------------

export interface MedicationOrder {
  id: string;
  order_number: string;
  patient: string;
  patient_name: string;
  medication_name: string;
  dose: string;
  dose_unit: string;
  route: string;
  frequency: string;
  status: string;
  start_date: string;
  end_date: string | null;
  ordering_provider_name: string;
  verified: boolean;
  special_instructions: string;
}

export interface PatientListParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: PatientStatus;
  ward?: string;
  physician?: string;
}

// ---------------------------------------------------------------------------
// Patient API
// ---------------------------------------------------------------------------

export function getPatients(params?: PatientListParams): Promise<PaginatedResponse<Patient>> {
  return apiClient.get('/api/v1/healthcare/patients/', { params });
}

export function getPatient(id: string): Promise<Patient> {
  return apiClient.get(`/api/v1/healthcare/patients/${id}/`);
}

export function createPatient(data: CreatePatientPayload): Promise<Patient> {
  return apiClient.post('/api/v1/healthcare/patients/', data);
}

export function admitPatient(id: string, data: AdmitPatientPayload): Promise<Patient> {
  return apiClient.post(`/api/v1/healthcare/patients/${id}/admit/`, data);
}

export function dischargePatient(id: string, notes?: string): Promise<Patient> {
  return apiClient.post(`/api/v1/healthcare/patients/${id}/discharge/`, { notes });
}

export function getPatientAllergies(patientId: string): Promise<PatientAllergy[]> {
  return apiClient.get(`/api/v1/healthcare/patients/${patientId}/allergies/`);
}

// ---------------------------------------------------------------------------
// Vital Signs API
// ---------------------------------------------------------------------------

export function getLatestVitals(patientId: string): Promise<VitalSigns> {
  return apiClient.get('/api/v1/healthcare/vital-signs/latest/', {
    params: { patient: patientId },
  });
}

export function getVitalsTrends(patientId: string, days = 7): Promise<VitalSigns[]> {
  return apiClient.get('/api/v1/healthcare/vital-signs/trends/', {
    params: { patient: patientId, days },
  });
}

export function getAbnormalVitals(patientId?: string): Promise<VitalSigns[]> {
  return apiClient.get('/api/v1/healthcare/vital-signs/abnormal/', {
    params: patientId ? { patient: patientId } : undefined,
  });
}

// ---------------------------------------------------------------------------
// Clinical Notes API
// ---------------------------------------------------------------------------

export function getClinicalNotes(
  patientId: string,
  noteType?: string
): Promise<PaginatedResponse<ClinicalNote>> {
  return apiClient.get('/api/v1/healthcare/clinical-notes/', {
    params: { patient: patientId, note_type: noteType },
  });
}

// ---------------------------------------------------------------------------
// Medication Orders API
// ---------------------------------------------------------------------------

export function getMedicationOrders(
  patientId: string
): Promise<PaginatedResponse<MedicationOrder>> {
  return apiClient.get('/api/v1/healthcare/medication-orders/', {
    params: { patient: patientId },
  });
}

export function getActiveMedicationOrders(
  patientId: string
): Promise<MedicationOrder[]> {
  return apiClient.get('/api/v1/healthcare/medication-orders/active/', {
    params: { patient: patientId },
  });
}
