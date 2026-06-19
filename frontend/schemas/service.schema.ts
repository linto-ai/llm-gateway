import { z } from 'zod';

// Test flavor schema (used by components/services/FlavorTestDialog.tsx).
// Service / flavor CRUD validation lives in schemas/forms.ts; the previous
// duplicate schemas here (serviceTypeSchema, createServiceSchema, flavorSchema,
// ...) were unused and carried a stale, divergent service-type enum, so they
// were removed.
export const testFlavorSchema = z.object({
  prompt: z.string().min(1, 'Prompt is required'),
});

export type TestFlavorFormData = z.infer<typeof testFlavorSchema>;
