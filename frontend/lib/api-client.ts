import { api } from './api';
import type { PaginatedResponse } from '@/types/api';
import type {
  ProviderResponse,
  CreateProviderRequest,
  UpdateProviderRequest,
  ProviderListFilters,
  VerifyModelsResponse,
} from '@/types/provider';
import type {
  ModelResponse,
  CreateModelRequest,
  UpdateModelRequest,
  ModelListFilters,
} from '@/types/model';
import type {
  ServiceResponse,
  CreateServiceRequest,
  UpdateServiceRequest,
  ServiceListFilters,
  CreateFlavorRequest,
  UpdateFlavorRequest,
  ExecuteServiceRequest,
  ExecuteServiceResponse,
  FallbackAvailabilityResponse,
  ExecutionValidationResponse,
} from '@/types/service';
import type {
  PromptResponse,
  CreatePromptRequest,
  UpdatePromptRequest,
  PromptListFilters,
  DuplicatePromptRequest,
} from '@/types/prompt';
import type {
  ServiceTemplateResponse,
  CreateFromTemplateRequest,
} from '@/types/template';
import type {
  DocumentTemplate,
  ExportFormat,
} from '@/types/document-template';
import type {
  JobResponse,
  JobListFilters,
  JobVersionSummary,
  JobVersionDetail,
  JobResultUpdate,
} from '@/types/job';
import type {
  SyntheticTemplatesResponse,
  SyntheticTemplateContent,
} from '@/types/synthetic';
import type { ServiceTypeConfig } from '@/types/service-type';
import type {
  PromptTypeResponse,
  CreatePromptTypeRequest,
  UpdatePromptTypeRequest,
  PromptTypeListFilters,
} from '@/types/prompt-type';

/**
 * API Client for LLM Gateway Backend
 * Provides type-safe methods for all CRUD operations
 */
export const apiClient = {
  // Generic methods for direct API access
  get: <T>(url: string, config?: { params?: Record<string, unknown> }): Promise<T> => {
    return api.get(url, config);
  },

  post: <T>(url: string, data?: unknown): Promise<T> => {
    return api.post(url, data);
  },

  patch: <T>(url: string, data?: unknown): Promise<T> => {
    return api.patch(url, data);
  },

  delete: <T>(url: string): Promise<T> => {
    return api.delete(url);
  },

  // ==================== PROVIDERS ====================
  providers: {
    list: async (filters?: ProviderListFilters): Promise<PaginatedResponse<ProviderResponse>> => {
      return api.get('/api/v1/providers', { params: filters });
    },

    get: async (id: string): Promise<ProviderResponse> => {
      return api.get(`/api/v1/providers/${id}`);
    },

    create: async (data: CreateProviderRequest): Promise<ProviderResponse> => {
      return api.post('/api/v1/providers', data);
    },

    update: async (id: string, data: UpdateProviderRequest): Promise<ProviderResponse> => {
      return api.patch(`/api/v1/providers/${id}`, data);
    },

    delete: async (id: string): Promise<void> => {
      return api.delete(`/api/v1/providers/${id}`);
    },

    verifyModels: async (providerId: string): Promise<VerifyModelsResponse> => {
      return api.post(`/api/v1/providers/${providerId}/models/verify`);
    },
  },

  // ==================== MODELS ====================
  models: {
    list: async (filters?: ModelListFilters): Promise<PaginatedResponse<ModelResponse>> => {
      return api.get('/api/v1/models', { params: filters });
    },

    get: async (id: string): Promise<ModelResponse> => {
      return api.get(`/api/v1/models/${id}`);
    },

    create: async (data: CreateModelRequest): Promise<ModelResponse> => {
      return api.post('/api/v1/models', data);
    },

    update: async (id: string, data: UpdateModelRequest): Promise<ModelResponse> => {
      return api.patch(`/api/v1/models/${id}`, data);
    },

    delete: async (id: string): Promise<void> => {
      return api.delete(`/api/v1/models/${id}`);
    },
  },

  // ==================== SERVICES ====================
  services: {
    list: async (filters?: ServiceListFilters): Promise<PaginatedResponse<ServiceResponse>> => {
      return api.get('/api/v1/services', { params: filters });
    },

    get: async (id: string): Promise<ServiceResponse> => {
      return api.get(`/api/v1/services/${id}`);
    },

    create: async (data: CreateServiceRequest): Promise<ServiceResponse> => {
      return api.post('/api/v1/services', data);
    },

    update: async (id: string, data: UpdateServiceRequest): Promise<ServiceResponse> => {
      return api.patch(`/api/v1/services/${id}`, data);
    },

    delete: async (id: string): Promise<void> => {
      return api.delete(`/api/v1/services/${id}`);
    },

    execute: async (serviceId: string, formData: FormData): Promise<ExecuteServiceResponse> => {
      return api.post(`/api/v1/services/${serviceId}/run`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    // Check fallback availability for a flavor
    checkFallbackAvailable: async (
      serviceId: string,
      flavorId: string
    ): Promise<FallbackAvailabilityResponse> => {
      return api.get(`/api/v1/services/${serviceId}/flavors/${flavorId}/fallback-available`);
    },

    // Validate execution (dry run) - check if content fits context limits
    validateExecution: async (
      serviceId: string,
      formData: FormData
    ): Promise<ExecutionValidationResponse> => {
      return api.post(`/api/v1/services/${serviceId}/validate-execution`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    // Flavor management
    addFlavor: async (serviceId: string, data: CreateFlavorRequest): Promise<ServiceResponse> => {
      return api.post(`/api/v1/services/${serviceId}/flavors`, data);
    },

    updateFlavor: async (serviceId: string, flavorId: string, data: UpdateFlavorRequest): Promise<ServiceResponse> => {
      return api.patch(`/api/v1/services/${serviceId}/flavors/${flavorId}`, data);
    },

    deleteFlavor: async (serviceId: string, flavorId: string): Promise<void> => {
      return api.delete(`/api/v1/services/${serviceId}/flavors/${flavorId}`);
    },
  },

  // ==================== PROMPTS ====================
  prompts: {
    list: async (filters?: PromptListFilters): Promise<PaginatedResponse<PromptResponse>> => {
      return api.get('/api/v1/prompts', {
        params: {
          page: filters?.page,
          page_size: filters?.page_size,
          organization_id: filters?.organization_id,
          name: filters?.search,
          service_type: filters?.service_type,
          prompt_category: filters?.prompt_category,
          prompt_type: filters?.prompt_type,
        },
      });
    },

    get: async (id: string): Promise<PromptResponse> => {
      return api.get(`/api/v1/prompts/${id}`);
    },

    create: async (data: CreatePromptRequest): Promise<PromptResponse> => {
      return api.post('/api/v1/prompts', data);
    },

    update: async (id: string, data: UpdatePromptRequest): Promise<PromptResponse> => {
      return api.patch(`/api/v1/prompts/${id}`, data);
    },

    delete: async (id: string): Promise<void> => {
      return api.delete(`/api/v1/prompts/${id}`);
    },

    duplicate: async (id: string, data: DuplicatePromptRequest): Promise<PromptResponse> => {
      return api.post(`/api/v1/prompts/${id}/duplicate`, data);
    },
  },

  // ==================== SERVICE TEMPLATES ====================
  templates: {
    list: async (filters?: { service_type?: string; is_public?: boolean }): Promise<{ templates: ServiceTemplateResponse[] }> => {
      return api.get('/api/v1/service-templates', { params: filters });
    },

    get: async (id: string): Promise<ServiceTemplateResponse> => {
      return api.get(`/api/v1/service-templates/${id}`);
    },

    instantiate: async (templateId: string, data: CreateFromTemplateRequest): Promise<ServiceResponse> => {
      return api.post(`/api/v1/services/from-template/${templateId}`, data);
    },
  },

  // ==================== JOBS ====================
  jobs: {
    get: async (jobId: string): Promise<JobResponse> => {
      return api.get(`/api/v1/jobs/${jobId}`);
    },

    list: async (filters?: JobListFilters): Promise<PaginatedResponse<JobResponse>> => {
      return api.get('/api/v1/jobs', { params: filters });
    },

    cancel: async (jobId: string): Promise<{ job_id: string; status: string; message: string }> => {
      return api.post(`/api/v1/jobs/${jobId}/cancel`);
    },

    delete: async (jobId: string): Promise<{ job_id: string; status: string; message: string }> => {
      return api.delete(`/api/v1/jobs/${jobId}`);
    },

    // Job version history methods
    updateResult: async (jobId: string, data: JobResultUpdate): Promise<JobResponse> => {
      return api.patch(`/api/v1/jobs/${jobId}/result`, data);
    },

    listVersions: async (jobId: string): Promise<JobVersionSummary[]> => {
      return api.get(`/api/v1/jobs/${jobId}/versions`);
    },

    getVersion: async (jobId: string, versionNumber: number): Promise<JobVersionDetail> => {
      return api.get(`/api/v1/jobs/${jobId}/versions/${versionNumber}`);
    },

    restoreVersion: async (jobId: string, versionNumber: number): Promise<JobResponse> => {
      return api.post(`/api/v1/jobs/${jobId}/versions/${versionNumber}/restore`);
    },

    // Export job to DOCX/PDF
    export: async (jobId: string, format: ExportFormat, templateId?: string): Promise<Blob> => {
      const params = templateId ? `?template_id=${templateId}` : '';
      const response = await api.get(`/api/v1/jobs/${jobId}/export/${format}${params}`, {
        responseType: 'blob',
      });
      return response as unknown as Blob;
    },

    // Extract metadata from completed job
    extractMetadata: async (
      jobId: string,
      promptId?: string,
      fields?: string[]
    ): Promise<JobResponse> => {
      const params: Record<string, unknown> = {};
      if (promptId) params.prompt_id = promptId;
      if (fields?.length) params.fields = fields;
      return api.post(`/api/v1/jobs/${jobId}/extract-metadata`, params);
    },
  },

  // ==================== HEALTH CHECK ====================
  health: {
    check: async (): Promise<{
      status: 'healthy' | 'unhealthy';
      database: 'connected' | 'disconnected';
      redis: 'connected' | 'disconnected';
      timestamp: string;
    }> => {
      return api.get('/healthcheck');
    },
  },

  // ==================== SYNTHETIC TEMPLATES ====================
  syntheticTemplates: {
    list: async (): Promise<SyntheticTemplatesResponse> => {
      return api.get('/api/v1/synthetic-templates');
    },

    getContent: async (filename: string): Promise<SyntheticTemplateContent> => {
      return api.get(`/api/v1/synthetic-templates/${filename}/content`);
    },
  },

  // ==================== SERVICE TYPES ====================
  serviceTypes: {
    list: async (): Promise<ServiceTypeConfig[]> => {
      return api.get('/api/v1/service-types');
    },

    get: async (serviceType: string): Promise<ServiceTypeConfig> => {
      return api.get(`/api/v1/service-types/${serviceType}`);
    },
  },

  // ==================== PROMPT TYPES ====================
  promptTypes: {
    list: async (filters?: PromptTypeListFilters): Promise<PromptTypeResponse[]> => {
      const params: Record<string, unknown> = {};
      if (filters?.active_only) params.active_only = true;
      return api.get('/api/v1/prompt-types', { params });
    },

    get: async (id: string): Promise<PromptTypeResponse> => {
      return api.get(`/api/v1/prompt-types/${id}`);
    },

    create: async (data: CreatePromptTypeRequest): Promise<PromptTypeResponse> => {
      return api.post('/api/v1/prompt-types', data);
    },

    update: async (id: string, data: UpdatePromptTypeRequest): Promise<PromptTypeResponse> => {
      return api.patch(`/api/v1/prompt-types/${id}`, data);
    },

    delete: async (id: string): Promise<void> => {
      return api.delete(`/api/v1/prompt-types/${id}`);
    },
  },

  // ==================== DOCUMENT TEMPLATES ====================
  documentTemplates: {
    list: async (serviceId?: string, options?: { includeGlobal?: boolean; globalOnly?: boolean }): Promise<DocumentTemplate[]> => {
      const params: Record<string, unknown> = {};
      if (serviceId) params.service_id = serviceId;
      if (options?.includeGlobal) params.include_global = true;
      if (options?.globalOnly) params.global_only = true;
      return api.get('/api/v1/templates', { params });
    },

    listGlobal: async (): Promise<DocumentTemplate[]> => {
      return api.get('/api/v1/templates', { params: { global_only: true } });
    },

    get: async (id: string): Promise<DocumentTemplate> => {
      return api.get(`/api/v1/templates/${id}`);
    },

    upload: async (formData: FormData): Promise<DocumentTemplate> => {
      return api.post('/api/v1/templates', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    delete: async (id: string): Promise<void> => {
      return api.delete(`/api/v1/templates/${id}`);
    },

    download: async (id: string): Promise<Blob> => {
      const response = await api.get(`/api/v1/templates/${id}/download`, {
        responseType: 'blob',
      });
      return response as unknown as Blob;
    },

    setDefault: async (templateId: string, serviceId: string): Promise<void> => {
      return api.post(`/api/v1/templates/${templateId}/set-default?service_id=${serviceId}`);
    },

    getPlaceholders: async (id: string): Promise<string[]> => {
      return api.get(`/api/v1/templates/${id}/placeholders`);
    },

    import: async (templateId: string, serviceId: string, newName?: string): Promise<DocumentTemplate> => {
      return api.post(`/api/v1/templates/${templateId}/import`, {
        service_id: serviceId,
        new_name: newName,
      });
    },
  },
};
