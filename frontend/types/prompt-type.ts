// Prompt Type types based on API contract

export interface PromptTypeResponse {
  id: string;
  code: string;
  name: Record<string, string>;  // {en, fr}
  description: Record<string, string>;
  is_system: boolean;
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface CreatePromptTypeRequest {
  code: string;
  name: { en: string; fr?: string };
  description?: { en?: string; fr?: string };
  is_active?: boolean;
  display_order?: number;
}

export interface UpdatePromptTypeRequest {
  name?: { en?: string; fr?: string };
  description?: { en?: string; fr?: string };
  is_active?: boolean;
  display_order?: number;
}

export interface PromptTypeListFilters {
  active_only?: boolean;
  service_type?: string;
}
