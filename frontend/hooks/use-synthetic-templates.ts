import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

/**
 * TanStack Query hooks for Synthetic Templates
 */

// List all available synthetic templates
export const useSyntheticTemplates = () => {
  return useQuery({
    queryKey: ['synthetic-templates'],
    queryFn: () => apiClient.syntheticTemplates.list(),
  });
};

// Get content of a specific synthetic template
export const useSyntheticTemplateContent = (filename: string | null) => {
  return useQuery({
    queryKey: ['synthetic-templates', filename, 'content'],
    queryFn: () => apiClient.syntheticTemplates.getContent(filename!),
    enabled: !!filename,
  });
};
