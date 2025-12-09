import { z } from 'zod';

export const executeServiceSchema = z.object({
  file: z.instanceof(File, { message: 'File is required' }),
  flavor_id: z.string().uuid('Invalid flavor ID'),
  temperature: z.number().min(0).max(2).optional(),
  top_p: z.number().min(0).max(1).optional(),
  // Free-form organization identifier (any string up to 100 chars)
  organization_id: z.string().max(100).optional(),
});

export type ExecuteServiceFormData = z.infer<typeof executeServiceSchema>;
