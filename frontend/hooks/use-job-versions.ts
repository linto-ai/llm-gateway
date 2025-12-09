import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { JobVersionSummary, JobVersionDetail, JobResponse } from '@/types/job';

/**
 * TanStack Query hooks for Job version history management.
 */

/**
 * List versions for a job
 */
export function useJobVersions(jobId: string) {
  return useQuery<JobVersionSummary[], Error>({
    queryKey: ['job-versions', jobId],
    queryFn: () => apiClient.jobs.listVersions(jobId),
    enabled: !!jobId,
  });
}

/**
 * Get specific version content
 */
export function useJobVersion(jobId: string, versionNumber: number) {
  return useQuery<JobVersionDetail, Error>({
    queryKey: ['job-versions', jobId, versionNumber],
    queryFn: () => apiClient.jobs.getVersion(jobId, versionNumber),
    enabled: !!jobId && versionNumber > 0,
  });
}

/**
 * Update job result content (creates new version)
 */
export function useUpdateJobResult(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation<JobResponse, Error, string>({
    mutationFn: (content: string) => apiClient.jobs.updateResult(jobId, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs', jobId] });
      queryClient.invalidateQueries({ queryKey: ['job-versions', jobId] });
    },
  });
}

/**
 * Restore job to a previous version
 */
export function useRestoreJobVersion(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation<JobResponse, Error, number>({
    mutationFn: (versionNumber: number) => apiClient.jobs.restoreVersion(jobId, versionNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs', jobId] });
      queryClient.invalidateQueries({ queryKey: ['job-versions', jobId] });
    },
  });
}
