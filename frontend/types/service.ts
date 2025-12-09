// Service and Flavor types based on API contract

// Processing mode type
export type ProcessingMode = 'single_pass' | 'iterative';

// Failover reason types
export type FailoverReason = 'timeout' | 'rate_limit' | 'model_error' | 'content_filter';

// Failover step in chain
export interface FailoverStep {
  from_flavor_id: string;
  from_flavor_name: string;
  to_flavor_id: string;
  to_flavor_name: string;
  reason: FailoverReason;
  error_message?: string;
  attempt_number: number;
  timestamp: string;
}

// Failover chain response
export interface FailoverChainResponse {
  chain: Array<{
    id: string;
    name: string;
    service_id: string;
    service_name: string;
    model_name: string;
    is_active: boolean;
    depth: number;
  }>;
  max_depth: number;
  has_cycle: boolean;
}

// Validate failover response
export interface ValidateFailoverResponse {
  valid: boolean;
  error?: string;
  chain_depth: number;
  chain_preview: string[];
}

export type ServiceType =
  | 'summary'
  | 'translation'
  | 'categorization'
  | 'diarization_correction'
  | 'speaker_correction'
  | 'generic';

export interface I18nDescription {
  en: string;
  fr: string;
}

export interface DocumentConfig {
  doc_title_prompt_id?: string;
  paragraph_title_prompt_id?: string;
}

// Canonical output types
export type OutputType = 'text' | 'markdown' | 'json';

export interface FlavorResponse {
  id: string;
  service_id: string;
  model_id: string;
  name: string;
  description?: string;
  temperature: number;
  top_p: number;
  is_default: boolean;
  is_active: boolean;

  // Advanced parameters
  frequency_penalty: number;
  presence_penalty: number;
  stop_sequences: string[];
  custom_params: Record<string, any>;
  estimated_cost_per_1k_tokens?: number;
  max_concurrent_requests?: number;
  priority: number;

  // Chunking configuration (for iterative processing)
  create_new_turn_after: number | null;
  summary_turns: number | null;
  max_new_turns: number | null;
  reduce_summary: boolean;
  consolidate_summary: boolean;

  output_type: string;

  // Template references (for tracking origin)
  system_prompt_id: string | null;
  user_prompt_template_id: string | null;
  reduce_prompt_id: string | null;

  // Inline prompt storage (actual content used)
  prompt_system_content: string | null;
  prompt_user_content: string | null;
  prompt_reduce_content: string | null;

  created_at: string;
  updated_at: string;

  // Tokenizer override
  tokenizer_override?: string;

  // Processing mode configuration
  processing_mode?: ProcessingMode;

  // Fallback configuration
  fallback_flavor_id?: string | null;
  fallback_flavor_name?: string | null;
  fallback_service_name?: string | null;

  // Prompt names for display (from backend eager loading)
  system_prompt_name?: string;
  user_prompt_template_name?: string;
  reduce_prompt_name?: string;

  // Model information (nested)
  model?: {
    id: string;
    model_name: string;
    model_identifier: string;
    provider_id: string;
    provider_name: string;
    context_length?: number;
    max_generation_length?: number;
  };

  // Placeholder extraction configuration
  placeholder_extraction_prompt_id?: string | null;
  placeholder_extraction_prompt_name?: string | null;

  // Categorization configuration
  categorization_prompt_id?: string | null;
  categorization_prompt_name?: string | null;

  // Failover configuration
  failover_flavor_id?: string;
  failover_flavor_name?: string;
  failover_service_name?: string;
  failover_enabled: boolean;
  failover_on_timeout: boolean;
  failover_on_rate_limit: boolean;
  failover_on_model_error: boolean;
  failover_on_content_filter: boolean;
  max_failover_depth: number;
}

export interface ServiceResponse {
  id: string;
  name: string;
  service_type: ServiceType;
  description: I18nDescription;
  organization_id: string;
  flavors: FlavorResponse[];
  created_at: string;
  updated_at: string;
}

export interface CreateFlavorRequest {
  name: string;
  model_id: string;
  description?: string;
  temperature: number;
  top_p: number;
  is_default: boolean;
  is_active?: boolean;
  output_type: OutputType;

  // Advanced parameters
  frequency_penalty?: number;
  presence_penalty?: number;
  stop_sequences?: string[];
  custom_params?: Record<string, any>;
  estimated_cost_per_1k_tokens?: number;
  max_concurrent_requests?: number;
  priority?: number;

  // Prompt options - Option 1: Load from template
  system_prompt_template_id?: string;
  user_prompt_template_id?: string;
  reduce_prompt_template_id?: string;

  // Prompt options - Option 2: Provide inline content
  prompt_system_content?: string;
  prompt_user_content?: string;
  prompt_reduce_content?: string;

  // Chunking configuration
  create_new_turn_after?: number;
  summary_turns?: number;
  max_new_turns?: number;
  reduce_summary?: boolean;
  consolidate_summary?: boolean;

  // Tokenizer override
  tokenizer_override?: string;

  // Processing mode configuration
  processing_mode?: ProcessingMode;

  // Fallback configuration
  fallback_flavor_id?: string;

  // Placeholder extraction configuration
  placeholder_extraction_prompt_id?: string;
}

export interface CreateServiceRequest {
  name: string;
  service_type: ServiceType;
  description: I18nDescription;
  organization_id: string;
  flavors: CreateFlavorRequest[];
}

export interface UpdateServiceRequest {
  name?: string;
  description?: Partial<I18nDescription>;
}

export interface UpdateFlavorRequest {
  name?: string;
  description?: string;
  temperature?: number;
  top_p?: number;
  is_default?: boolean;
  is_active?: boolean;
  output_type?: OutputType;

  // Advanced parameters
  frequency_penalty?: number;
  presence_penalty?: number;
  stop_sequences?: string[];
  custom_params?: Record<string, any>;
  estimated_cost_per_1k_tokens?: number;
  max_concurrent_requests?: number;
  priority?: number;

  // Inline prompt editing (edits local copy, not template)
  prompt_system_content?: string;
  prompt_user_content?: string;
  prompt_reduce_content?: string;

  // Template replacement (replaces inline content with template)
  system_prompt_template_id?: string;
  user_prompt_template_id?: string;
  reduce_prompt_template_id?: string;

  // Tokenizer override
  tokenizer_override?: string;

  // Processing mode configuration
  processing_mode?: ProcessingMode;

  // Fallback configuration
  fallback_flavor_id?: string | null;

  // Placeholder extraction configuration
  placeholder_extraction_prompt_id?: string;
}

export interface ServiceListFilters {
  organization_id?: string;
  service_type?: ServiceType;
  page?: number;
  page_size?: number;
}

export interface ExecuteServiceRequest {
  text: string;
  file_name?: string;
  [key: string]: any;
}

// Execute response with fallback tracking
export interface ExecuteServiceResponse {
  job_id: string;
  status: 'queued';
  service_id: string;
  service_name: string;
  flavor_id: string;
  flavor_name: string;
  created_at: string;
  estimated_completion_time?: string;

  // Fallback tracking fields
  fallback_applied: boolean;
  original_flavor_id?: string;
  original_flavor_name?: string;
  fallback_reason?: string;
  input_tokens?: number;
  context_available?: number;
}

// Fallback availability check response
export interface FallbackAvailabilityResponse {
  fallback_available: boolean;
  fallback_flavor_id?: string;
  fallback_flavor_name?: string;
  reason?: string;
}

// Execution error response with typed error codes
export type ExecutionErrorCode =
  | 'CONTEXT_EXCEEDED'
  | 'CONTEXT_EXCEEDED_NO_FALLBACK'
  | 'FLAVOR_INACTIVE'
  | 'FALLBACK_FLAVOR_INACTIVE';

export interface ExecutionErrorResponse {
  detail: string;
  error_code: ExecutionErrorCode;
  input_tokens?: number;
  available_tokens?: number;
  flavor_id?: string;
  flavor_name?: string;
  original_flavor_id?: string;
  suggestion?: string;
}

// Flavor Testing Types
export interface FlavorTestRequest {
  prompt: string;
}

export interface FlavorTestResponse {
  flavor_id: string;
  flavor_name: string;
  model: {
    model_name: string;
    model_identifier: string;
    provider_name: string;
  };
  request: {
    prompt: string;
    temperature: number;
    max_tokens: number;
    top_p: number;
    frequency_penalty: number;
    presence_penalty: number;
    stop_sequences: string[];
  };
  response: {
    content: string;
    finish_reason: string;
  };
  metadata: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    latency_ms: number;
    estimated_cost: number;
  };
  timestamp: string;
}

// Flavor Analytics Types
export interface FlavorStats {
  flavor_id: string;
  flavor_name: string;
  period: string;
  stats: {
    total_requests: number;
    successful_requests: number;
    failed_requests: number;
    success_rate: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_tokens: number;
    avg_input_tokens: number;
    avg_output_tokens: number;
    avg_latency_ms: number;
    min_latency_ms: number;
    max_latency_ms: number;
    p50_latency_ms: number;
    p95_latency_ms: number;
    p99_latency_ms: number;
    total_estimated_cost: number;
    avg_cost_per_request: number;
    time_series: Array<{
      timestamp: string;
      requests: number;
      tokens: number;
      cost: number;
    }>;
  };
  generated_at: string;
}

export interface ServiceFlavorComparison {
  service_id: string;
  service_name: string;
  period: string;
  flavors: Array<{
    flavor_id: string;
    flavor_name: string;
    is_default: boolean;
    total_requests: number;
    success_rate: number;
    total_tokens: number;
    avg_latency_ms: number;
    total_estimated_cost: number;
    usage_percentage: number;
  }>;
  totals: {
    total_requests: number;
    total_tokens: number;
    total_cost: number;
  };
  generated_at: string;
}

export interface FlavorUsageHistoryItem {
  id: string;
  flavor_id: string;
  job_id?: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  latency_ms: number;
  estimated_cost: number;
  success: boolean;
  error_message?: string;
  executed_at: string;
}

export interface FlavorUsageHistoryResponse {
  total: number;
  items: FlavorUsageHistoryItem[];
}

// Execution validation (dry run) response
export interface ExecutionValidationResponse {
  valid: boolean;
  warning: string | null;
  input_tokens: number | null;
  max_generation: number | null;
  context_length: number | null;
  estimated_cost: number | null;
}
