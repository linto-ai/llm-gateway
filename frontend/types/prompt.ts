// Prompt types based on API contract

import type { PromptTypeResponse } from './prompt-type';

// Category type (fixed enum) - how prompt is used in LLM calls
export type PromptCategory = 'system' | 'user';

export interface PromptResponse {
  id: string;
  name: string;
  content: string;
  description: Record<string, string>; // i18n {en, fr}
  organization_id: string | null;

  // Service type affinity (required)
  service_type: string;

  // Category and type fields
  prompt_category: PromptCategory;
  prompt_type: PromptTypeResponse | null;

  // Parent template reference
  parent_template_id: string | null;

  // Computed field: number of {} placeholders in content
  // Used to filter prompts by processing mode:
  // - single_pass: requires 1 placeholder
  // - iterative: requires 2 placeholders
  placeholder_count: number;

  created_at: string;
  updated_at: string;
}

export interface CreatePromptRequest {
  name: string;
  content: string;
  description?: Record<string, string>;
  organization_id?: string;
  service_type: string;
  prompt_category: PromptCategory;
  prompt_type?: string;
}

export interface UpdatePromptRequest {
  content?: string;
  description?: Record<string, string>;
  service_type?: string;
  prompt_category?: PromptCategory;
  prompt_type?: string | null;
}

export interface DuplicatePromptRequest {
  new_name: string;
  organization_id?: string;
}

export interface SaveAsTemplateRequest {
  template_name: string;
  category: PromptCategory;
  prompt_type?: string;
  description?: {
    en?: string;
    fr?: string;
  };
}

export interface PromptListFilters {
  organization_id?: string | null;
  search?: string;
  page?: number;
  page_size?: number;
  // Filters
  service_type?: string;
  prompt_category?: PromptCategory;
  prompt_type?: string;
}

export interface PromptTemplateFilters {
  category?: PromptCategory;
  page?: number;
  page_size?: number;
  // Filters
  service_type?: string;
  prompt_type?: string;
}
