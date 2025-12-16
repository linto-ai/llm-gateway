import { z } from 'zod';

/**
 * Form validation schemas for all CRUD operations
 * Uses Zod for runtime validation with React Hook Form
 */

// ==================== PROVIDER SCHEMAS ====================

export const providerFormSchema = z.object({
  name: z.string()
    .min(1, 'validation.required')
    .max(100, 'validation.maxLength'),
  provider_type: z.enum(['openai', 'anthropic', 'cohere', 'openrouter', 'custom']),
  api_base_url: z.string().url('validation.invalidUrl'),
  api_key: z.string().optional(), // Optional because it can be empty when updating
  security_level: z.enum(['secure', 'sensitive', 'insecure']),
  metadata: z.record(z.any()).optional(),
});

export type ProviderFormData = z.infer<typeof providerFormSchema>;

// ==================== MODEL SCHEMAS ====================

export const modelFormSchema = z.object({
  name: z.string()
    .min(1, 'validation.required')
    .max(200, 'validation.maxLength'),
  display_name: z.string().min(1, 'validation.required').max(200, 'validation.maxLength'),
  provider_id: z.string().uuid('validation.invalidUuid'),
  // Free-form organization identifier (any string up to 100 chars)
  organization_id: z.string().max(100, 'validation.maxLength').nullable().optional(),
  security_level: z.enum(['secure', 'sensitive', 'insecure']).nullable().optional(),
  tokenizer_name: z.string().max(200).nullable().optional(),
  metadata: z.record(z.any()).optional(),
});

export type ModelFormData = z.infer<typeof modelFormSchema>;

// ==================== FLAVOR SCHEMAS ====================

export const flavorFormSchema = z.object({
  name: z.string().min(1, 'validation.required').max(100, 'validation.maxLength'),
  model_id: z.string().uuid('validation.invalidUuid'),
  description: z.string().optional(),
  is_default: z.boolean().default(false),
  is_active: z.boolean().default(true),
  temperature: z.number().min(0, 'validation.min').max(2, 'validation.max'),
  top_p: z.number().min(0, 'validation.min').max(1, 'validation.max'),
  // Canonical output types
  output_type: z.enum(['text', 'markdown', 'json']).default('text'),

  // Advanced parameters
  frequency_penalty: z.number().min(0, 'validation.min').max(2, 'validation.max').default(0),
  presence_penalty: z.number().min(0, 'validation.min').max(2, 'validation.max').default(0),
  stop_sequences: z.array(z.string()).default([]),
  custom_params: z.record(z.any()).default({}),
  estimated_cost_per_1k_tokens: z.number().positive('validation.min').nullable().optional(),
  max_concurrent_requests: z.number().int().positive('validation.min').nullable().optional(),
  priority: z.number().int().min(0, 'validation.min').default(0),

  // Template reference fields
  system_prompt_id: z.string().nullable().optional(),
  user_prompt_template_id: z.string().nullable().optional(),
  reduce_prompt_id: z.string().nullable().optional(),

  // Inline content fields
  prompt_system_content: z.string().optional(),
  prompt_user_content: z.string().optional(),
  prompt_reduce_content: z.string().optional(),

  // Chunking parameters
  create_new_turn_after: z.number()
    .int()
    .min(1, 'validation.min')
    .default(100)
    .nullable()
    .optional(),
  max_new_turns: z.number()
    .int()
    .min(1, 'validation.min')
    .nullable()
    .optional(),
  summary_turns: z.number()
    .int()
    .min(1, 'validation.min')
    .nullable()
    .optional(),
  reduce_summary: z.boolean().default(false),
  consolidate_summary: z.boolean().default(false),

  // Processing mode
  processing_mode: z.enum(['single_pass', 'iterative']).default('iterative'),

  // Fallback configuration
  fallback_flavor_id: z.string().uuid('validation.invalidUuid').nullable().optional(),

  // Tokenizer override
  tokenizer_override: z.string().max(100).optional(),

  // Placeholder extraction configuration
  placeholder_extraction_prompt_id: z.string().uuid('validation.invalidUuid').nullable().optional(),

  // Categorization configuration
  categorization_prompt_id: z.string().uuid('validation.invalidUuid').nullable().optional(),

  // Failover configuration
  failover_flavor_id: z.string().uuid('validation.invalidUuid').nullable().optional(),
  failover_enabled: z.boolean().default(false),
  failover_on_timeout: z.boolean().default(true),
  failover_on_rate_limit: z.boolean().default(true),
  failover_on_model_error: z.boolean().default(true),
  failover_on_content_filter: z.boolean().default(false),
  max_failover_depth: z.number().int().min(1).max(10).default(3),

  // Job TTL configuration (null = never expire)
  default_ttl_seconds: z.number()
    .int()
    .positive('validation.positive')
    .max(31536000, 'validation.maxTtl')  // 1 year in seconds
    .nullable()
    .optional(),
});

export type FlavorFormData = z.infer<typeof flavorFormSchema>;

// ==================== SERVICE SCHEMAS ====================

export const serviceFormSchema = z.object({
  name: z.string()
    .min(1, 'validation.required')
    .max(100, 'validation.maxLength'),
  service_type: z.enum([
    'summary',
    'translation',
    'categorization',
    'diarization_correction',
    'speaker_correction',
    'generic',
  ]),
  description: z.object({
    en: z.string().optional().default(''),
    fr: z.string().optional().default(''),
  }),
  // Free-form organization identifier (any string up to 100 chars)
  organization_id: z.string().max(100, 'validation.maxLength').nullable().optional(),
  // Flavors are optional during creation - can be added later via Flavors tab
  flavors: z.array(flavorFormSchema).optional().default([]),
});

export type ServiceFormData = z.infer<typeof serviceFormSchema>;

// ==================== PROMPT SCHEMAS ====================

export const promptFormSchema = z.object({
  name: z.string()
    .min(1, 'validation.required')
    .max(100, 'validation.maxLength'),
  content: z.string().min(1, 'validation.required'),
  description: z.object({
    en: z.string().min(1, 'validation.required'),
    fr: z.string().min(1, 'validation.required'),
  }),
  // service_type is REQUIRED
  service_type: z.enum([
    'summary',
    'translation',
    'categorization',
    'diarization_correction',
    'speaker_correction',
    'generic',
  ]),
  // prompt_category is REQUIRED (system or user)
  prompt_category: z.enum(['system', 'user']),
  // prompt_type is OPTIONAL (code string, common: standard, reduce)
  prompt_type: z.string().max(100).nullable().optional(),
  // Free-form organization identifier (any string up to 100 chars)
  organization_id: z.string().max(100, 'validation.maxLength').nullable().optional(),
});

export type PromptFormData = z.infer<typeof promptFormSchema>;

// ==================== DUPLICATE PROMPT SCHEMA ====================

export const duplicatePromptSchema = z.object({
  new_name: z.string().min(1, 'validation.required').max(100, 'validation.maxLength'),
  // Free-form organization identifier (any string up to 100 chars)
  organization_id: z.string().max(100, 'validation.maxLength').optional(),
});

export type DuplicatePromptData = z.infer<typeof duplicatePromptSchema>;

// ==================== TEMPLATE INSTANTIATION SCHEMA ====================

export const instantiateTemplateSchema = z.object({
  name: z.string().min(1, 'validation.required').max(100, 'validation.maxLength'),
  // Free-form organization identifier (any string up to 100 chars)
  organization_id: z.string().max(100, 'validation.maxLength').nullable().optional(),
  model_id: z.string().uuid('validation.invalidUuid'),
  description: z.object({
    en: z.string().optional(),
    fr: z.string().optional(),
  }).optional(),
});

export type InstantiateTemplateData = z.infer<typeof instantiateTemplateSchema>;

// ==================== VERSION ROLLBACK SCHEMA ====================

export const rollbackVersionSchema = z.object({
  change_description: z.string().max(500, 'validation.maxLength').optional(),
});

export type RollbackVersionData = z.infer<typeof rollbackVersionSchema>;

// ==================== SERVICE EXECUTION SCHEMA ====================

export const executeServiceSchema = z.object({
  text: z.string().min(1, 'validation.required'),
  file_name: z.string().optional(),
});

export type ExecuteServiceData = z.infer<typeof executeServiceSchema>;
