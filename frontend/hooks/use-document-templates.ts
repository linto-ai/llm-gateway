import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  DocumentTemplate,
  ExportFormat,
  TemplateQueryParams,
  ExportPreview,
  PlaceholderInfo,
} from '@/types/document-template';
import type { JobResponse } from '@/types/job';

/**
 * TanStack Query hooks for Document Template management and Job export.
 */

// ==================== DOCUMENT TEMPLATES ====================

/**
 * Fetch document templates with hierarchical visibility
 */
export const useDocumentTemplates = (params?: TemplateQueryParams) => {
  return useQuery({
    queryKey: ['document-templates', params],
    queryFn: () => apiClient.documentTemplates.list(params),
    staleTime: 0,
    refetchOnMount: true,
  });
};

/**
 * Fetch system templates (org_id=null, user_id=null)
 */
export const useSystemDocumentTemplates = () => {
  return useQuery({
    queryKey: ['document-templates', 'system'],
    queryFn: () => apiClient.documentTemplates.listSystem(),
    select: (data) => data,
  });
};

/**
 * Fetch global document templates (template library) - legacy alias
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
 * Update a document template (metadata and/or file)
 */
export const useUpdateDocumentTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, formData }: { id: string; formData: FormData }) =>
      apiClient.documentTemplates.update(id, formData),
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
 * Set a template as the global default (for exports without service-specific default)
 */
export const useSetGlobalDefaultDocumentTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) =>
      apiClient.documentTemplates.setGlobalDefault(templateId),
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
 * Get template placeholders
 */
export const useTemplatePlaceholders = (templateId: string | undefined) => {
  return useQuery({
    queryKey: ['document-templates', templateId, 'placeholders'],
    queryFn: () => apiClient.documentTemplates.getPlaceholders(templateId!),
    enabled: !!templateId,
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
      versionNumber,
      fileName,
    }: {
      jobId: string;
      format: ExportFormat;
      templateId?: string;
      versionNumber?: number;
      fileName?: string;
    }) => {
      const blob = await apiClient.jobs.export(jobId, format, templateId, versionNumber);
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

/**
 * Preview export placeholders and extraction status
 */
export const useExportPreview = (jobId: string, templateId?: string) => {
  return useQuery({
    queryKey: ['export-preview', jobId, templateId],
    queryFn: () => apiClient.exportPreview.get(jobId, templateId),
    enabled: !!jobId,
  });
};
