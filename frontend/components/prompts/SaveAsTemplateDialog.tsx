'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { usePromptTypes } from '@/hooks/use-prompt-types';
import type { SaveAsTemplateRequest, PromptCategory } from '@/types/prompt';

interface SaveAsTemplateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  promptContent: string;
  defaultCategory?: PromptCategory;
  defaultPromptType?: string;
  onSave: (data: SaveAsTemplateRequest) => Promise<void>;
}

const saveTemplateSchema = z.object({
  template_name: z.string().min(1, 'Template name is required').max(100, 'Template name is too long'),
  category: z.enum(['system', 'user']),
  prompt_type: z.string().max(100).optional(),
  description_en: z.string().max(500, 'Description is too long').optional(),
  description_fr: z.string().max(500, 'Description is too long').optional(),
});

type SaveTemplateFormData = z.infer<typeof saveTemplateSchema>;

export function SaveAsTemplateDialog({
  open,
  onOpenChange,
  promptContent,
  defaultCategory = 'user',
  defaultPromptType,
  onSave,
}: SaveAsTemplateDialogProps) {
  const t = useTranslations('prompts.saveAsTemplate');
  const tCategory = useTranslations('prompts.category');
  const tPromptType = useTranslations('prompts.promptType');
  const tCommon = useTranslations('common');

  // Fetch prompt types for dropdown
  const { data: promptTypes } = usePromptTypes({ active_only: true });

  const form = useForm<SaveTemplateFormData>({
    resolver: zodResolver(saveTemplateSchema),
    defaultValues: {
      template_name: '',
      category: defaultCategory,
      prompt_type: defaultPromptType || '',
      description_en: '',
      description_fr: '',
    },
  });

  const onSubmit = async (data: SaveTemplateFormData) => {
    const payload: SaveAsTemplateRequest = {
      template_name: data.template_name,
      category: data.category,
      prompt_type: data.prompt_type || undefined,
      description: {},
    };

    if (data.description_en) {
      payload.description!.en = data.description_en;
    }
    if (data.description_fr) {
      payload.description!.fr = data.description_fr;
    }

    try {
      await onSave(payload);
      form.reset();
      onOpenChange(false);
    } catch (error) {
      // Error handled by parent
    }
  };

  const isSubmitting = form.formState.isSubmitting;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('title')}</DialogTitle>
          <DialogDescription>
            {tCommon('description')}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="template_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('templateName')} *</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="My Template" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('category')} *</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="system">{tCategory('system')}</SelectItem>
                      <SelectItem value="user">{tCategory('user')}</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="prompt_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('promptType')}</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value || ''}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t('promptTypePlaceholder')} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="">{t('promptTypeNone')}</SelectItem>
                      {promptTypes?.map((pt) => (
                        <SelectItem key={pt.id} value={pt.code}>
                          {pt.name.en || pt.code}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description_en"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('descriptionEn')}</FormLabel>
                  <FormControl>
                    <Textarea {...field} rows={3} placeholder="English description..." />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description_fr"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('descriptionFr')}</FormLabel>
                  <FormControl>
                    <Textarea {...field} rows={3} placeholder="Description francaise..." />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {tCommon('cancel')}
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('saving')}
                  </>
                ) : (
                  t('save')
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
