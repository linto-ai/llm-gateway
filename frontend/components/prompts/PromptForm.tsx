'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations, useLocale } from 'next-intl';

import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';

import { useCreatePrompt, useUpdatePrompt } from '@/hooks/use-prompts';
import { useServiceTypes } from '@/hooks/use-service-types';
import { usePromptTypes } from '@/hooks/use-prompt-types';
import { promptFormSchema, type PromptFormData } from '@/schemas/forms';
import type { PromptResponse } from '@/types/prompt';

interface PromptFormProps {
  prompt?: PromptResponse;
  onSuccess: () => void;
  onCancel: () => void;
  duplicateMode?: boolean;
}

export function PromptForm({ prompt, onSuccess, onCancel, duplicateMode = false }: PromptFormProps) {
  const t = useTranslations('prompts');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  const createMutation = useCreatePrompt();
  const updateMutation = useUpdatePrompt();
  const { data: serviceTypes } = useServiceTypes();
  // Only load prompt types for 'summary' service type (prompt types are only used with summary)
  const { data: promptTypes } = usePromptTypes({ service_type: 'summary', active_only: true });

  // Helper to get a valid service_type (required)
  const getDefaultServiceType = (): 'summary' | 'translation' | 'categorization' | 'diarization_correction' | 'speaker_correction' | 'generic' => {
    if (prompt?.service_type) {
      return prompt.service_type as 'summary' | 'translation' | 'categorization' | 'diarization_correction' | 'speaker_correction' | 'generic';
    }
    return 'summary'; // Default for new prompts
  };

  // Helper to get default category
  const getDefaultCategory = (): 'system' | 'user' => {
    if (prompt?.prompt_category) {
      return prompt.prompt_category;
    }
    return 'user'; // Default for new prompts
  };

  const form = useForm<PromptFormData>({
    resolver: zodResolver(promptFormSchema),
    defaultValues: {
      name: duplicateMode ? '' : (prompt?.name || ''),
      content: prompt?.content || '',
      description: {
        en: prompt?.description.en || '',
        fr: prompt?.description.fr || '',
      },
      // service_type is required
      service_type: getDefaultServiceType(),
      // prompt_category is required
      prompt_category: getDefaultCategory(),
      // prompt_type is optional (use code from nested object)
      prompt_type: prompt?.prompt_type?.code || null,
      organization_id: prompt?.organization_id || undefined,
    },
  });

  // Watch service_type to conditionally show prompt_type
  const serviceType = form.watch('service_type');

  // Clear prompt_type when service_type changes away from 'summary'
  useEffect(() => {
    if (serviceType !== 'summary') {
      form.setValue('prompt_type', null);
    }
  }, [serviceType, form]);

  const onSubmit = async (data: PromptFormData) => {
    try {
      if (prompt && !duplicateMode) {
        // Update existing prompt
        await updateMutation.mutateAsync({
          id: prompt.id,
          data: {
            content: data.content,
            description: data.description,
            prompt_category: data.prompt_category,
            prompt_type: data.prompt_type || null,
          },
        });
      } else {
        // Create new prompt (or duplicate)
        // Ensure organization_id is undefined not null for API
        await createMutation.mutateAsync({
          ...data,
          organization_id: data.organization_id ?? undefined,
          prompt_type: data.prompt_type || undefined,
        });
      }
      onSuccess();
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Name */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.name')}</FormLabel>
              <FormControl>
                <Input
                  placeholder={
                    duplicateMode && prompt
                      ? t('placeholders.newName', { name: prompt.name })
                      : t('placeholders.name')
                  }
                  {...field}
                  disabled={!!prompt && !duplicateMode}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Service Type - required */}
        <FormField
          control={form.control}
          name="service_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('serviceType')} *</FormLabel>
              <Select
                onValueChange={field.onChange}
                value={field.value || ''}
                disabled={!!prompt && !duplicateMode}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder={t('selectServiceType')} />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {serviceTypes?.map((st) => (
                    <SelectItem key={st.code} value={st.code}>
                      {locale === 'fr' ? (st.name.fr || st.name.en) : st.name.en}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>{t('serviceTypeHelp')}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Prompt Category - required (System / User) */}
        <FormField
          control={form.control}
          name="prompt_category"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.category')} *</FormLabel>
              <Select
                onValueChange={field.onChange}
                value={field.value}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="system">{t('category.system')}</SelectItem>
                  <SelectItem value="user">{t('category.user')}</SelectItem>
                </SelectContent>
              </Select>
              <FormDescription>{t('categoryHelp')}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Prompt Type - optional, only shown for summary service type */}
        {serviceType === 'summary' && (
          <FormField
            control={form.control}
            name="prompt_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('fields.promptType')}</FormLabel>
                <Select
                  onValueChange={(value) => field.onChange(value === 'none' ? null : value)}
                  value={field.value || 'none'}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder={t('promptTypePlaceholder')} />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="none">{t('promptTypeNone')}</SelectItem>
                    {promptTypes?.map((pt) => (
                      <SelectItem key={pt.id} value={pt.code}>
                        {locale === 'fr' ? (pt.name.fr || pt.name.en) : pt.name.en}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormDescription>{t('promptTypeHelp')}</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        )}

        {/* Content */}
        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.content')}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder={t('placeholders.content')}
                  rows={10}
                  className="font-mono text-sm"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Description (English) */}
        <FormField
          control={form.control}
          name="description.en"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.descriptionEn')}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="English description"
                  rows={2}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Description (French) */}
        <FormField
          control={form.control}
          name="description.fr"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.descriptionFr')}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Description francaise"
                  rows={2}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            {tCommon('cancel')}
          </Button>
          <Button
            type="submit"
            disabled={createMutation.isPending || updateMutation.isPending}
          >
            {prompt && !duplicateMode ? tCommon('update') : tCommon('create')}
          </Button>
        </div>
      </form>
    </Form>
  );
}
