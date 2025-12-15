// Document Template types

/**
 * Template scope indicating visibility level
 */
export type TemplateScope = 'system' | 'organization' | 'user';

/**
 * Document template response from API (updated schema with i18n)
 */
export interface DocumentTemplate {
  id: string;
  name_fr: string;
  name_en: string | null;
  description_fr: string | null;
  description_en: string | null;
  organization_id: string | null;
  user_id: string | null;
  file_name: string;
  file_size: number;
  file_hash: string;
  mime_type: string;
  placeholders: string[];
  is_default: boolean;
  scope: TemplateScope;
  created_at: string;
  updated_at: string;
}

/**
 * Query parameters for listing templates
 */
export interface TemplateQueryParams {
  organization_id?: string;
  user_id?: string;
  include_system?: boolean;
  include_all?: boolean;
  service_id?: string;
}

/**
 * Form data for template upload (i18n fields)
 */
export interface DocumentTemplateUpload {
  file: File;
  name_fr: string;
  name_en?: string;
  description_fr?: string;
  description_en?: string;
  organization_id?: string;
  user_id?: string;
  is_default?: boolean;
}

/**
 * Form data for template update
 */
export interface DocumentTemplateUpdate {
  file?: File;
  name_fr?: string;
  name_en?: string;
  description_fr?: string;
  description_en?: string;
  is_default?: boolean;
}

/**
 * Placeholder info with metadata
 */
export interface PlaceholderInfo {
  name: string;
  description: string | null;
  is_standard: boolean;
}

/**
 * Placeholder status for export preview
 */
export interface PlaceholderStatus {
  name: string;
  status: 'available' | 'missing' | 'extraction_required';
  value?: string;
}

/**
 * Export preview response
 */
export interface ExportPreview {
  template_id: string;
  template_name: string;
  placeholders: PlaceholderStatus[];
  extraction_required: boolean;
  estimated_extraction_tokens?: number;
}

/**
 * Export preview request
 */
export interface ExportPreviewRequest {
  template_id?: string;
}

/**
 * Legacy: Request to create a new template (via multipart form data)
 * @deprecated Use DocumentTemplateUpload instead
 */
export interface DocumentTemplateCreate {
  name: string;
  description?: string;
  service_id: string;
  is_default?: boolean;
}

/**
 * Legacy: Form data fields for template upload
 * @deprecated Use DocumentTemplateUpload instead
 */
export interface DocumentTemplateUploadFields {
  name: string;
  description?: string;
  service_id: string;
  is_default: boolean;
  file: File;
}

/**
 * Standard placeholders available in templates
 */
export const STANDARD_PLACEHOLDERS = [
  'output',
  'job_id',
  'job_date',
  'service_name',
  'flavor_name',
  'organization_name',
  'generated_at',
] as const;

/**
 * Metadata placeholders (from extraction)
 */
export const METADATA_PLACEHOLDERS = [
  'title',
  'summary',
  'participants',
  'topics',
  'action_items',
  'key_points',
  'date',
  'sentiment',
] as const;

/**
 * Standard metadata fields for extraction configuration
 */
export const STANDARD_METADATA_FIELDS = [
  'title',
  'summary',
  'participants',
  'date',
  'topics',
  'action_items',
  'sentiment',
  'language',
  'word_count',
  'key_points',
] as const;

export type StandardPlaceholder = (typeof STANDARD_PLACEHOLDERS)[number];
export type MetadataPlaceholder = (typeof METADATA_PLACEHOLDERS)[number];
export type StandardMetadataField = (typeof STANDARD_METADATA_FIELDS)[number];

/**
 * Export format options
 */
export type ExportFormat = 'docx' | 'pdf';

/**
 * Parse a placeholder string that may contain a description.
 * Format: "field_name" or "field_name: description text"
 *
 * @param placeholder - The full placeholder string
 * @returns Object with name and optional description
 */
export function parsePlaceholder(placeholder: string): { name: string; description?: string } {
  const colonIndex = placeholder.indexOf(':');
  if (colonIndex === -1) {
    return { name: placeholder.trim() };
  }
  return {
    name: placeholder.substring(0, colonIndex).trim(),
    description: placeholder.substring(colonIndex + 1).trim() || undefined,
  };
}

/**
 * Get the display name for a placeholder (without description).
 */
export function getPlaceholderName(placeholder: string): string {
  return parsePlaceholder(placeholder).name;
}
