import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  ProviderResponse,
  CreateProviderRequest,
  UpdateProviderRequest,
  ProviderListFilters,
} from '@/types/provider';

/**
 * TanStack Query hooks for Provider CRUD operations
 */

// List providers with filters
export const useProviders = (filters?: ProviderListFilters) => {
  return useQuery({
    queryKey: ['providers', filters],
    queryFn: () => apiClient.providers.list(filters),
  });
};

// Get single provider
export const useProvider = (id: string | undefined) => {
  return useQuery({
    queryKey: ['providers', id],
    queryFn: () => apiClient.providers.get(id!),
    enabled: !!id,
  });
};

// Create provider mutation
export const useCreateProvider = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateProviderRequest) => apiClient.providers.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
  });
};

// Update provider mutation
export const useUpdateProvider = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateProviderRequest }) =>
      apiClient.providers.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      queryClient.invalidateQueries({ queryKey: ['providers', variables.id] });
    },
  });
};

// Delete provider mutation
export const useDeleteProvider = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.providers.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
  });
};

// Verify provider models mutation
export const useVerifyProviderModels = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (providerId: string) => apiClient.providers.verifyModels(providerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
  });
};
