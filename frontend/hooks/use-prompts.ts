import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  PromptResponse,
  CreatePromptRequest,
  UpdatePromptRequest,
  PromptListFilters,
  DuplicatePromptRequest,
  SaveAsTemplateRequest,
  PromptTemplateFilters,
} from '@/types/prompt';
import type { PaginatedResponse } from '@/types/api';

/**
 * TanStack Query hooks for Prompt CRUD operations.
 */

// List prompts with filters
export const usePrompts = (filters?: PromptListFilters) => {
  return useQuery({
    queryKey: ['prompts', filters],
    queryFn: () => apiClient.prompts.list(filters),
  });
};

// Get single prompt
export const usePrompt = (id: string | undefined) => {
  return useQuery({
    queryKey: ['prompts', id],
    queryFn: () => apiClient.prompts.get(id!),
    enabled: !!id,
  });
};

// Create prompt mutation
export const useCreatePrompt = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreatePromptRequest) => apiClient.prompts.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
};

// Update prompt mutation
export const useUpdatePrompt = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdatePromptRequest }) =>
      apiClient.prompts.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      queryClient.invalidateQueries({ queryKey: ['prompts', variables.id] });
    },
  });
};

// Delete prompt mutation
export const useDeletePrompt = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.prompts.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
};

// Duplicate prompt mutation
export const useDuplicatePrompt = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DuplicatePromptRequest }) =>
      apiClient.prompts.duplicate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
};

// List prompt templates with filters
export const usePromptTemplates = (filters?: PromptTemplateFilters) => {
  return useQuery({
    queryKey: ['prompts', 'templates', filters],
    queryFn: () =>
      apiClient.get<PaginatedResponse<PromptResponse>>('/api/v1/prompts/templates', {
        params: {
          category: filters?.category,
          page: filters?.page,
          page_size: filters?.page_size,
          service_type: filters?.service_type,
        },
      }),
  });
};

// Save prompt as template
export const useSaveAsTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ promptId, data }: { promptId: string; data: SaveAsTemplateRequest }) =>
      apiClient.post<PromptResponse>(`/api/v1/prompts/${promptId}/save-as-template`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts', 'templates'] });
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
};
