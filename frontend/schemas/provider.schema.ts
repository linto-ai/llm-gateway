import { z } from 'zod';

export const providerTypeSchema = z.enum([
  'openai',
  'anthropic',
  'cohere',
  'openrouter',
  'custom',
]);

export const securityLevelSchema = z.enum(['secure', 'sensitive', 'insecure']);

export const createProviderSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be at most 100 characters'),
  provider_type: providerTypeSchema,
  api_base_url: z.string().url('Must be a valid URL'),
  api_key: z.string().min(1, 'API key is required'),
  security_level: securityLevelSchema,
  metadata: z.record(z.any()).optional(),
});

export const updateProviderSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  provider_type: providerTypeSchema.optional(),
  api_base_url: z.string().url().optional(),
  api_key: z.string().min(1).optional(),
  security_level: securityLevelSchema.optional(),
  metadata: z.record(z.any()).optional(),
});

export type CreateProviderFormData = z.infer<typeof createProviderSchema>;
export type UpdateProviderFormData = z.infer<typeof updateProviderSchema>;
