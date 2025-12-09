// Document Template types

/**
 * Document template response from API
 */
export interface DocumentTemplate {
  id: string;
  name: string;
  description?: string;
  service_id?: string;
  organization_id?: string;
  file_name: string;
  file_size: number;
  placeholders?: string[];
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Request to create a new template (via multipart form data)
 */
export interface DocumentTemplateCreate {
  name: string;
  description?: string;
  service_id: string;
  is_default?: boolean;
}

/**
 * Form data fields for template upload
 * Actual upload uses FormData with file attachment
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
