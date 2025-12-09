import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  PromptTypeResponse,
  CreatePromptTypeRequest,
  UpdatePromptTypeRequest,
  PromptTypeListFilters,
} from '@/types/prompt-type';

/**
 * TanStack Query hooks for Prompt Type CRUD operations.
 */

// List prompt types
export function usePromptTypes(filters?: PromptTypeListFilters) {
  return useQuery({
    queryKey: ['prompt-types', filters],
    queryFn: async (): Promise<PromptTypeResponse[]> => {
      const params: Record<string, unknown> = {};
      if (filters?.active_only) params.active_only = true;
      if (filters?.service_type) params.service_type = filters.service_type;
      return api.get('/api/v1/prompt-types', { params });
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - types rarely change
  });
}

// Get single prompt type
export function usePromptType(id: string | undefined) {
  return useQuery({
    queryKey: ['prompt-types', id],
    queryFn: async (): Promise<PromptTypeResponse> => {
      return api.get(`/api/v1/prompt-types/${id}`);
    },
    enabled: !!id,
  });
}

// Create mutation
export function useCreatePromptType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreatePromptTypeRequest): Promise<PromptTypeResponse> => {
      return api.post('/api/v1/prompt-types', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt-types'] });
    },
  });
}

// Update mutation
export function useUpdatePromptType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdatePromptTypeRequest }): Promise<PromptTypeResponse> => {
      return api.patch(`/api/v1/prompt-types/${id}`, data);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['prompt-types'] });
      queryClient.invalidateQueries({ queryKey: ['prompt-types', variables.id] });
    },
  });
}

// Delete mutation
export function useDeletePromptType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      return api.delete(`/api/v1/prompt-types/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt-types'] });
    },
  });
}
