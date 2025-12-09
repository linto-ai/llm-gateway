import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  ServiceResponse,
  CreateServiceRequest,
  UpdateServiceRequest,
  ServiceListFilters,
  CreateFlavorRequest,
  UpdateFlavorRequest,
  ExecuteServiceRequest,
  FlavorTestRequest,
  FlavorTestResponse,
  FlavorStats,
  ServiceFlavorComparison,
  FlavorUsageHistoryResponse,
  FallbackAvailabilityResponse,
  ExecutionValidationResponse,
} from '@/types/service';

/**
 * TanStack Query hooks for Service CRUD operations and flavor management
 */

// List services with filters
export const useServices = (filters?: ServiceListFilters) => {
  return useQuery({
    queryKey: ['services', filters],
    queryFn: () => apiClient.services.list(filters),
  });
};

// Get single service (includes flavors)
export const useService = (id: string | undefined) => {
  return useQuery({
    queryKey: ['services', id],
    queryFn: () => apiClient.services.get(id!),
    enabled: !!id,
  });
};

// Create service mutation
export const useCreateService = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateServiceRequest) => apiClient.services.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });
};

// Update service mutation
export const useUpdateService = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateServiceRequest }) =>
      apiClient.services.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['services', variables.id] });
    },
  });
};

// Delete service mutation
export const useDeleteService = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.services.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });
};

// Execute service mutation
export const useExecuteService = () => {
  return useMutation({
    mutationFn: ({ serviceName, data }: { serviceName: string; data: FormData }) =>
      apiClient.services.execute(serviceName, data),
  });
};

// ==================== FLAVOR MANAGEMENT ====================

// Add flavor to service
export const useAddFlavor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ serviceId, data }: { serviceId: string; data: CreateFlavorRequest }) =>
      apiClient.services.addFlavor(serviceId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['services', variables.serviceId] });
    },
  });
};

// Update flavor
export const useUpdateFlavor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ serviceId, flavorId, data }: { serviceId: string; flavorId: string; data: UpdateFlavorRequest }) =>
      apiClient.services.updateFlavor(serviceId, flavorId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['services', variables.serviceId] });
    },
  });
};

// Delete flavor
export const useDeleteFlavor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ serviceId, flavorId }: { serviceId: string; flavorId: string }) =>
      apiClient.services.deleteFlavor(serviceId, flavorId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['services', variables.serviceId] });
    },
  });
};

// Set flavor as default
export const useSetDefaultFlavor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ serviceId, flavorId }: { serviceId: string; flavorId: string }) =>
      apiClient.post(`/api/v1/flavors/${flavorId}/set-default`),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['services', variables.serviceId] });
    },
  });
};

// ==================== FLAVOR TESTING & ANALYTICS ====================

// Get flavor details by ID
export const useFlavor = (flavorId: string | undefined) => {
  return useQuery({
    queryKey: ['flavors', flavorId],
    queryFn: () => apiClient.get<{ flavor: any }>(`/api/v1/flavors/${flavorId}`),
    enabled: !!flavorId,
  });
};

// Test flavor with sample prompt
export const useTestFlavor = () => {
  return useMutation({
    mutationFn: ({ flavorId, data }: { flavorId: string; data: FlavorTestRequest }) =>
      apiClient.post<FlavorTestResponse>(`/api/v1/flavors/${flavorId}/test`, data),
  });
};

// Get flavor usage statistics
export const useFlavorStats = (flavorId: string | undefined, period: '24h' | '7d' | '30d' | 'all' = '24h') => {
  return useQuery({
    queryKey: ['flavor-stats', flavorId, period],
    queryFn: () => apiClient.get<FlavorStats>(`/api/v1/flavors/${flavorId}/stats?period=${period}`),
    enabled: !!flavorId,
  });
};

// Get service flavor comparison
export const useServiceFlavorComparison = (serviceId: string | undefined, period: '24h' | '7d' | '30d' | 'all' = '24h') => {
  return useQuery({
    queryKey: ['service-flavor-comparison', serviceId, period],
    queryFn: () => apiClient.get<ServiceFlavorComparison>(`/api/v1/services/${serviceId}/flavor-stats?period=${period}`),
    enabled: !!serviceId,
  });
};

// Get flavor usage history
export const useFlavorUsageHistory = (
  flavorId: string | undefined,
  limit: number = 100,
  offset: number = 0
) => {
  return useQuery({
    queryKey: ['flavor-usage-history', flavorId, limit, offset],
    queryFn: () =>
      apiClient.get<FlavorUsageHistoryResponse>(
        `/api/v1/flavors/${flavorId}/usage-history?limit=${limit}&offset=${offset}`
      ),
    enabled: !!flavorId,
  });
};

// ==================== FALLBACK AVAILABILITY ====================

// Check if iterative fallback is available for a flavor
export const useFallbackAvailable = (
  serviceId: string | undefined,
  flavorId: string | undefined
) => {
  return useQuery({
    queryKey: ['fallback-available', serviceId, flavorId],
    queryFn: () => apiClient.services.checkFallbackAvailable(serviceId!, flavorId!),
    enabled: !!serviceId && !!flavorId,
    staleTime: 30000, // 30 seconds cache
  });
};

// Helper hook to check if service has any iterative fallback flavor (local check from service data)
export const useServiceHasIterativeFallback = (
  service: { flavors: Array<{ id: string; is_active: boolean; processing_mode?: string }> } | undefined,
  excludeFlavorId: string | undefined
) => {
  if (!service?.flavors) return false;
  return service.flavors.some(
    (f) =>
      f.id !== excludeFlavorId &&
      f.is_active &&
      f.processing_mode === 'iterative'
  );
};

// ==================== EXECUTION VALIDATION (DRY RUN) ====================

// Validate execution without making LLM calls - checks context window fit
export const useValidateExecution = () => {
  return useMutation({
    mutationFn: ({ serviceId, formData }: { serviceId: string; formData: FormData }) =>
      apiClient.services.validateExecution(serviceId, formData),
  });
};
