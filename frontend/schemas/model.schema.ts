import { z } from 'zod';

export const createModelSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be at most 100 characters'),
  display_name: z
    .string()
    .min(1, 'Display name is required')
    .max(200, 'Display name must be at most 200 characters'),
  provider_id: z.string().uuid('Must be a valid UUID'),
  // Free-form organization identifier (any string up to 100 chars)
  organization_id: z.string().max(100, 'Must be at most 100 characters').optional(),
  metadata: z.record(z.any()).optional(),
});

export const updateModelSchema = z.object({
  display_name: z.string().min(1).max(200).optional(),
  metadata: z.record(z.any()).optional(),
});

export type CreateModelFormData = z.infer<typeof createModelSchema>;
export type UpdateModelFormData = z.infer<typeof updateModelSchema>;
