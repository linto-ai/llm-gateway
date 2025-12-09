import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  ServiceTemplateResponse,
  CreateFromTemplateRequest,
  TemplateListFilters,
} from '@/types/template';

/**
 * TanStack Query hooks for Service Template operations
 * Templates are read-only with instantiation capability
 */

// List templates with filters
export const useTemplates = (filters?: TemplateListFilters) => {
  return useQuery({
    queryKey: ['templates', filters],
    queryFn: () => apiClient.templates.list(filters),
  });
};

// Get single template
export const useTemplate = (id: string | undefined) => {
  return useQuery({
    queryKey: ['templates', id],
    queryFn: () => apiClient.templates.get(id!),
    enabled: !!id,
  });
};

// Instantiate service from template
export const useInstantiateTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ templateId, data }: { templateId: string; data: CreateFromTemplateRequest }) =>
      apiClient.templates.instantiate(templateId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });
};
