// Synthetic template types based on API contract

export interface SyntheticTemplate {
  filename: string;
  language: 'en' | 'fr' | 'mixed';
  error_type: 'perfect' | 'diarization_errors' | 'full_errors';
  description: string;
  size_bytes: number;
}

export interface SyntheticTemplatesResponse {
  templates: SyntheticTemplate[];
}

export interface SyntheticTemplateContent {
  filename: string;
  content: string;
  language: string;
  error_type: string;
}
