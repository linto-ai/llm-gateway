// Provider types based on API contract

export type ProviderType = 'openai' | 'anthropic' | 'cohere' | 'openrouter' | 'custom';
export type SecurityLevel = 'secure' | 'sensitive' | 'insecure';

export interface ProviderResponse {
  id: string;
  name: string;
  provider_type: ProviderType;
  api_base_url: string;
  api_key_exists: boolean;
  security_level: SecurityLevel;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CreateProviderRequest {
  name: string;
  provider_type: ProviderType;
  api_base_url: string;
  api_key: string;
  security_level: SecurityLevel;
  metadata?: Record<string, any>;
}

export interface UpdateProviderRequest {
  name?: string;
  provider_type?: ProviderType;
  api_base_url?: string;
  api_key?: string;
  security_level?: SecurityLevel;
  metadata?: Record<string, any>;
}

export interface ProviderListFilters {
  provider_type?: ProviderType;
  security_level?: SecurityLevel;
  page?: number;
  page_size?: number;
}

export interface VerifyModelsResponse {
  provider_id: string;
  verified_models: Array<{
    model_id: string;
    model_name: string;
    is_verified: boolean;
    error_message?: string;
  }>;
  verification_timestamp: string;
}
