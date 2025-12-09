// Service Type configuration types

export interface PromptFieldConfig {
  required: boolean;
  template_category: string;
  description_en: string;
  description_fr: string;
}

export interface ServiceTypeConfig {
  type: string;
  name_en: string;
  name_fr: string;
  description_en: string;
  description_fr: string;
  prompts: Record<string, PromptFieldConfig>;
  supports_reduce: boolean;
  supports_chunking: boolean;
  default_processing_mode: string;
}

// New database-driven response type from /api/v1/service-types
export interface ServiceTypeResponse {
  id: string;
  code: string;
  name: Record<string, string>;  // {en, fr}
  description: Record<string, string>;
  is_system: boolean;
  is_active: boolean;
  display_order: number;
  supports_reduce: boolean;
  supports_chunking: boolean;
  default_processing_mode: string;
  created_at: string;
  updated_at: string;
}
