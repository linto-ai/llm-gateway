import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { ServiceTypeResponse, ServiceTypeConfig } from '@/types/service-type';

/**
 * TanStack Query hooks for Service Types (database-driven).
 */

// Fetch all service types from database
export function useServiceTypes(activeOnly: boolean = false) {
  return useQuery({
    queryKey: ['service-types', { activeOnly }],
    queryFn: async (): Promise<ServiceTypeResponse[]> => {
      const params = activeOnly ? '?active_only=true' : '';
      return api.get(`/api/v1/service-types${params}`);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Fetch specific service type by ID
export function useServiceType(id: string | undefined) {
  return useQuery({
    queryKey: ['service-type', id],
    queryFn: async (): Promise<ServiceTypeResponse> => {
      return api.get(`/api/v1/service-types/${id}`);
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

interface ServiceTemplateListResponse {
  items: Array<{
    id: string;
    name: string;
    service_type: string;
    description: Record<string, string>;
    is_public: boolean;
    default_config: Record<string, unknown>;
    created_at: string;
    updated_at: string;
  }>;
}

/**
 * Fetch service type config by code.
 * Uses the /config/{code} endpoint which returns prompt field requirements
 * from the backend SERVICE_TYPE_CONFIGS registry.
 */
export function useServiceTypeConfig(serviceType: string | undefined) {
  return useQuery({
    queryKey: ['service-type-config', serviceType],
    queryFn: async (): Promise<ServiceTypeConfig | null> => {
      try {
        return await api.get(`/api/v1/service-types/config/${serviceType}`);
      } catch {
        // Fallback: fetch from DB if config endpoint returns 404 (custom types)
        const serviceTypes: ServiceTypeResponse[] = await api.get('/api/v1/service-types');
        const found = serviceTypes.find(st => st.code === serviceType);
        if (!found) return null;
        return {
          type: found.code,
          name_en: found.name?.en || found.code,
          name_fr: found.name?.fr || found.code,
          description_en: found.description?.en || '',
          description_fr: found.description?.fr || '',
          prompts: {},
          supports_reduce: found.supports_reduce,
          supports_chunking: found.supports_chunking,
          default_processing_mode: found.default_processing_mode,
        };
      }
    },
    enabled: !!serviceType,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
