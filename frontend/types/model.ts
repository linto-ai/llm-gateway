// Model types based on API contract

import type { SecurityLevel } from './provider';

export type HealthStatus = 'available' | 'unavailable' | 'unknown' | 'error';

export interface ModelResponse {
  id: string;
  provider_id: string;
  provider_name?: string;
  model_name: string;
  model_identifier: string;
  context_length: number;
  max_generation_length: number;
  tokenizer_class: string | null;
  tokenizer_name: string | null;
  is_active: boolean;

  // Health status fields
  health_status: HealthStatus;
  health_checked_at: string | null;
  health_error: string | null;

  model_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;

  // Extended metadata fields
  huggingface_repo?: string | null;
  security_level?: SecurityLevel | null;
  deployment_name?: string | null;
  description?: string | null;
  best_use?: string | null;
  usage_type?: string | null;
  system_prompt?: string | null;
}

export interface ModelVerificationResponse {
  model_id: string;
  health_status: HealthStatus;
  checked_at: string;
  error: string | null;
  details: {
    latency_ms?: number;
    provider_response?: string;
  };
}

export interface DiscoveredModel {
  model_identifier: string;
  model_name: string;
  context_length: number;
  max_generation_length: number;
  tokenizer_class: string | null;
  tokenizer_name: string | null;
  available: boolean;
  // Extended metadata from provider APIs
  description?: string | null;
  best_use?: string | null;
  sensitivity_level?: string | null;
  default_for?: string[] | null;
  usage_type?: string | null;
  system_prompt?: string | null;
  deployment_name?: string | null;
  custom_tokenizer?: string | null;
  metadata?: Record<string, any> | null;
}

export interface CreateModelRequest {
  provider_id: string;
  model_name: string;
  model_identifier: string;
  context_length: number;
  max_generation_length: number;
  tokenizer_class?: string | null;
  tokenizer_name?: string | null;
  is_active?: boolean;
  model_metadata?: Record<string, any>;
  security_level?: SecurityLevel | null;
}

export interface UpdateModelRequest {
  model_name?: string;
  model_identifier?: string;
  context_length?: number;
  max_generation_length?: number;
  tokenizer_class?: string | null;
  tokenizer_name?: string | null;
  is_active?: boolean;
  model_metadata?: Record<string, any>;
  // Extended metadata fields
  huggingface_repo?: string | null;
  security_level?: SecurityLevel | null;
  deployment_name?: string | null;
  description?: string | null;
  best_use?: string | null;
  usage_type?: string | null;
  system_prompt?: string | null;
}

export interface ModelListFilters {
  provider_id?: string;
  health_status?: HealthStatus;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}
