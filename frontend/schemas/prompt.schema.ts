import { z } from 'zod';
import { i18nDescriptionSchema } from './service.schema';

export const createPromptSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be at most 100 characters'),
  content: z.string().min(1, 'Content is required'),
  description: i18nDescriptionSchema,
  // Free-form organization identifier (any string up to 100 chars)
  organization_id: z.string().max(100).optional(),
});

export const updatePromptSchema = z.object({
  content: z.string().min(1).optional(),
  description: i18nDescriptionSchema.partial().optional(),
});

export const duplicatePromptSchema = z.object({
  new_name: z.string().min(1, 'Name is required').max(100, 'Name must be at most 100 characters'),
  // Free-form organization identifier (any string up to 100 chars)
  organization_id: z.string().max(100).optional(),
});

export type CreatePromptFormData = z.infer<typeof createPromptSchema>;
export type UpdatePromptFormData = z.infer<typeof updatePromptSchema>;
export type DuplicatePromptFormData = z.infer<typeof duplicatePromptSchema>;
