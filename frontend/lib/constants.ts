// API_BASE_URL can be set at runtime via entrypoint script (replaces placeholder)
const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || '__NEXT_API_URL_PLACEHOLDER__';
export const API_BASE_URL = rawApiUrl === '__NEXT_API_URL_PLACEHOLDER__' ? 'http://localhost:8000' : rawApiUrl;
// WS_BASE_URL can be set at runtime via entrypoint script (replaces placeholder)
const rawWsUrl = process.env.NEXT_PUBLIC_WS_URL || '__NEXT_WS_URL_PLACEHOLDER__';
export const WS_BASE_URL = rawWsUrl === '__NEXT_WS_URL_PLACEHOLDER__' ? 'ws://localhost:8000' : rawWsUrl;
export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'LLM Gateway';
export const DEFAULT_LOCALE = process.env.NEXT_PUBLIC_DEFAULT_LOCALE || 'en';
// BASE_PATH can be set at runtime via entrypoint script (replaces placeholder)
const rawBasePath = process.env.NEXT_PUBLIC_BASE_PATH || '';
export const BASE_PATH = rawBasePath === '/__NEXT_BASEPATH_PLACEHOLDER__' ? '' : rawBasePath;

export const PROVIDER_TYPES = [
  'openai',
  'anthropic',
  'cohere',
  'openrouter',
  'custom',
] as const;

export const SECURITY_LEVELS = [
  'secure',
  'sensitive',
  'insecure',
] as const;

export const SERVICE_TYPES = [
  'summary',
  'translation',
  'categorization',
  'diarization_correction',
  'speaker_correction',
  'extraction',
  'generic',
] as const;

export const JOB_STATUSES = [
  'queued',
  'started',
  'processing',
  'completed',
  'failed',
] as const;

export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'fr', name: 'Français' },
  { code: 'es', name: 'Español' },
  { code: 'de', name: 'Deutsch' },
  { code: 'it', name: 'Italiano' },
  { code: 'pt', name: 'Português' },
] as const;

export const PAGE_SIZES = [10, 25, 50, 100] as const;
export const DEFAULT_PAGE_SIZE = 50;
export const MAX_PAGE_SIZE = 100;

export const FILE_UPLOAD_MAX_SIZE = 10 * 1024 * 1024; // 10MB
export const FILE_UPLOAD_ACCEPTED_TYPES = ['.txt', '.md', '.json'];

export const QUERY_STALE_TIME = 5 * 60 * 1000; // 5 minutes
export const QUERY_CACHE_TIME = 10 * 60 * 1000; // 10 minutes
