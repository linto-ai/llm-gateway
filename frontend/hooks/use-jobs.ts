import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { JobResponse, JobListFilters } from '@/types/job';

/**
 * TanStack Query hooks for Job operations and service execution
 */

interface ExecuteServiceParams {
  serviceId: string;
  flavorId: string;
  file?: File;
  syntheticTemplate?: string;
  temperature?: number;
  top_p?: number;
  organization_id?: string;
}

// Execute service with file upload
export const useExecuteService = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      serviceId,
      flavorId,
      file,
      syntheticTemplate,
      temperature,
      top_p,
      organization_id,
    }: ExecuteServiceParams) => {
      const formData = new FormData();
      formData.append('flavor_id', flavorId);

      // Either file or synthetic template, not both
      if (syntheticTemplate) {
        formData.append('synthetic_template', syntheticTemplate);
      } else if (file) {
        formData.append('file', file);
      }

      if (temperature !== undefined) formData.append('temperature', String(temperature));
      if (top_p !== undefined) formData.append('top_p', String(top_p));
      if (organization_id) formData.append('organization_id', organization_id);

      return apiClient.services.execute(serviceId, formData);
    },
    onSuccess: () => {
      // Invalidate jobs list
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
};

// Get single job with optional polling
export const useJob = (
  jobId: string | null,
  options?: { refetchInterval?: number | false | ((data: JobResponse | null | undefined) => number | false) }
) => {
  return useQuery<JobResponse | null, Error>({
    queryKey: ['jobs', jobId],
    queryFn: async (): Promise<JobResponse | null> => {
      if (!jobId) return null;
      return apiClient.jobs.get(jobId);
    },
    enabled: !!jobId,
    refetchInterval: options?.refetchInterval as number | false | undefined,
  });
};

// List jobs with filters and auto-refresh for active jobs
export const useJobs = (filters?: JobListFilters, options?: { refetchInterval?: number | false }) => {
  return useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => apiClient.jobs.list(filters),
    // Auto-refresh every 10 seconds by default (fallback when WebSocket available)
    // Can be overridden via options
    refetchInterval: options?.refetchInterval ?? 10000,
  });
};

// Cancel a job
export const useCancelJob = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => apiClient.jobs.cancel(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
};

// Delete a job
export const useDeleteJob = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => apiClient.jobs.delete(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
};
