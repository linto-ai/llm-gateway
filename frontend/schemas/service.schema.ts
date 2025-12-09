import { z } from 'zod';

export const serviceTypeSchema = z.enum([
  'summary',
  'document',
  'translation',
  'categorization',
  'diarization_correction',
  'speaker_detection',
]);

export const i18nDescriptionSchema = z.object({
  en: z.string().min(1, 'English description is required'),
  fr: z.string().min(1, 'French description is required'),
});

// Stop sequences validation
export const stopSequencesSchema = z
  .array(z.string())
  .max(4, 'Maximum 4 stop sequences allowed')
  .default([]);

// Custom params validation
export const customParamsSchema = z
  .record(z.any())
  .refine(
    (val) => {
      try {
        JSON.stringify(val);
        return true;
      } catch {
        return false;
      }
    },
    { message: 'Invalid JSON format' }
  )
  .default({});

export const flavorSchema = z.object({
  name: z.string().min(1, 'Name is required').max(50, 'Name must be at most 50 characters'),
  model_id: z.string().uuid('Must be a valid UUID'),
  description: z.string().max(500, 'Description must be at most 500 characters').optional(),
  is_default: z.boolean().default(false),
  is_active: z.boolean().default(true),

  // Model parameters
  temperature: z
    .number()
    .min(0, 'Must be at least 0')
    .max(2, 'Must be at most 2')
    .default(0.7),
  top_p: z
    .number()
    .min(0, 'Must be at least 0')
    .max(1, 'Must be at most 1')
    .default(0.9),

  // Advanced parameters
  frequency_penalty: z
    .number()
    .min(0, 'Must be at least 0')
    .max(2, 'Must be at most 2')
    .default(0.0),
  presence_penalty: z
    .number()
    .min(0, 'Must be at least 0')
    .max(2, 'Must be at most 2')
    .default(0.0),
  stop_sequences: stopSequencesSchema,
  custom_params: customParamsSchema,
  estimated_cost_per_1k_tokens: z.number().positive('Must be positive').optional(),
  max_concurrent_requests: z.number().int().positive('Must be positive integer').optional(),
  priority: z.number().int().min(0, 'Must be at least 0').default(0),

  // Prompt references
  system_prompt_id: z.string().uuid().optional().nullable(),
  user_prompt_template_id: z.string().uuid().optional().nullable(),
  reduce_prompt_id: z.string().uuid().optional().nullable(),
});

export const createServiceSchema = z
  .object({
    name: z.string().min(1, 'Name is required').max(100, 'Name must be at most 100 characters'),
    service_type: serviceTypeSchema,
    description: i18nDescriptionSchema,
    // Free-form organization identifier (any string up to 100 chars)
    organization_id: z.string().max(100, 'Must be at most 100 characters').optional(),
    flavors: z.array(flavorSchema).min(1, 'At least one flavor is required'),
  })
;

export const updateServiceSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  description: i18nDescriptionSchema.partial().optional(),
});

export const updateFlavorSchema = flavorSchema.partial();

// Test flavor schema
export const testFlavorSchema = z.object({
  prompt: z.string().min(1, 'Prompt is required'),
});

export type CreateServiceFormData = z.infer<typeof createServiceSchema>;
export type UpdateServiceFormData = z.infer<typeof updateServiceSchema>;
export type FlavorFormData = z.infer<typeof flavorSchema>;
export type UpdateFlavorFormData = z.infer<typeof updateFlavorSchema>;
export type TestFlavorFormData = z.infer<typeof testFlavorSchema>;
