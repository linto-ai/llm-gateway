import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { DocumentTemplate, ExportFormat } from '@/types/document-template';
import type { JobResponse } from '@/types/job';

/**
 * TanStack Query hooks for Document Template management and Job export.
 */

// ==================== DOCUMENT TEMPLATES ====================

/**
 * Fetch document templates, optionally filtered by service
 * Note: API returns DocumentTemplate[] directly, not wrapped in { templates: [...] }
 */
export const useDocumentTemplates = (serviceId?: string, options?: { includeGlobal?: boolean }) => {
  return useQuery({
    queryKey: ['document-templates', serviceId, options?.includeGlobal],
    queryFn: () => apiClient.documentTemplates.list(serviceId, { includeGlobal: options?.includeGlobal }),
    select: (data) => data, // Return array directly
  });
};

/**
 * Fetch global document templates (template library)
 */
export const useGlobalDocumentTemplates = () => {
  return useQuery({
    queryKey: ['document-templates', 'global'],
    queryFn: () => apiClient.documentTemplates.listGlobal(),
    select: (data) => data,
  });
};

/**
 * Fetch a single document template
 */
export const useDocumentTemplate = (id: string | undefined) => {
  return useQuery({
    queryKey: ['document-templates', id],
    queryFn: () => apiClient.documentTemplates.get(id!),
    enabled: !!id,
  });
};

/**
 * Upload a new document template
 */
export const useUploadDocumentTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => apiClient.documentTemplates.upload(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-templates'] });
    },
  });
};

/**
 * Delete a document template
 */
export const useDeleteDocumentTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.documentTemplates.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-templates'] });
    },
  });
};

/**
 * Set a template as default for a service
 */
export const useSetDefaultDocumentTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ templateId, serviceId }: { templateId: string; serviceId: string }) =>
      apiClient.documentTemplates.setDefault(templateId, serviceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-templates'] });
    },
  });
};

/**
 * Import a global template to a service
 */
export const useImportDocumentTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ templateId, serviceId, newName }: { templateId: string; serviceId: string; newName?: string }) =>
      apiClient.documentTemplates.import(templateId, serviceId, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-templates'] });
    },
  });
};

/**
 * Download a template file
 */
export const useDownloadDocumentTemplate = () => {
  return useMutation({
    mutationFn: async ({ id, fileName }: { id: string; fileName: string }) => {
      const blob = await apiClient.documentTemplates.download(id);
      // Trigger browser download
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      return blob;
    },
  });
};

// ==================== JOB EXPORT ====================

/**
 * Export a job result to DOCX or PDF
 */
export const useExportJob = () => {
  return useMutation({
    mutationFn: async ({
      jobId,
      format,
      templateId,
      fileName,
    }: {
      jobId: string;
      format: ExportFormat;
      templateId?: string;
      fileName?: string;
    }) => {
      const blob = await apiClient.jobs.export(jobId, format, templateId);
      // Trigger browser download
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName || `job-${jobId}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      return blob;
    },
  });
};

// ==================== METADATA EXTRACTION ====================

/**
 * Extract metadata from a completed job
 */
export const useExtractJobMetadata = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      jobId,
      promptId,
      fields,
    }: {
      jobId: string;
      promptId?: string;
      fields?: string[];
    }) => apiClient.jobs.extractMetadata(jobId, promptId, fields),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['jobs', variables.jobId] });
    },
  });
};
