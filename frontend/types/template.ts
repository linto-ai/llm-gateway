// Service Template types based on API contract

import { ServiceType, I18nDescription, ServiceResponse } from './service';

export interface ServiceTemplateResponse {
  id: string;
  name: string;
  service_type: ServiceType;
  description: I18nDescription;
  is_public: boolean;
  default_config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CreateFromTemplateRequest {
  name: string;
  organization_id: string;
  model_id: string;
  description?: Partial<I18nDescription>;
}

export interface TemplateListFilters {
  service_type?: ServiceType;
  is_public?: boolean;
}
