import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { apiClient } from '@/lib/api-client';
import type {
  ModelResponse,
  CreateModelRequest,
  UpdateModelRequest,
  ModelListFilters,
  ModelVerificationResponse,
  DiscoveredModel,
} from '@/types/model';

/**
 * TanStack Query hooks for Model CRUD operations
 */

// List models with filters
export const useModels = (filters?: ModelListFilters) => {
  return useQuery({
    queryKey: ['models', filters],
    queryFn: () => apiClient.models.list(filters),
  });
};

// Get single model
export const useModel = (id: string | undefined) => {
  return useQuery({
    queryKey: ['models', id],
    queryFn: () => apiClient.models.get(id!),
    enabled: !!id,
  });
};

// Create model mutation
export const useCreateModel = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateModelRequest) => apiClient.models.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
  });
};

// Update model mutation
export const useUpdateModel = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateModelRequest }) =>
      apiClient.models.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      queryClient.invalidateQueries({ queryKey: ['models', variables.id] });
    },
  });
};

// Delete model mutation
export const useDeleteModel = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.models.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
  });
};

// Verify model health
export const useVerifyModel = () => {
  const queryClient = useQueryClient();
  return useMutation<ModelVerificationResponse, Error, string>({
    mutationFn: async (modelId: string) => {
      // The api interceptor unwraps the response, so response is already the data
      const response = await api.post(`/api/v1/models/${modelId}/verify`);
      return response as unknown as ModelVerificationResponse;
    },
    onSuccess: (data, modelId) => {
      queryClient.invalidateQueries({ queryKey: ['models', modelId] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
  });
};

// Discover provider models
export const useDiscoverProviderModels = () => {
  return useMutation<DiscoveredModel[], Error, string>({
    mutationFn: async (providerId: string) => {
      // The api interceptor unwraps the response, so response is already the data
      const response = await api.get(`/api/v1/providers/${providerId}/discover-models`);
      return response as unknown as DiscoveredModel[];
    },
  });
};
