'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';
import { modelFormSchema, type ModelFormData } from '@/schemas/forms';
import { useCreateModel, useUpdateModel } from '@/hooks/use-models';
import { useProviders } from '@/hooks/use-providers';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { toast } from 'sonner';
import { useRouter } from '@/lib/navigation';
import type { ModelResponse } from '@/types/model';

interface ModelFormProps {
  model?: ModelResponse;
  locale: string;
  onSuccess?: () => void | Promise<void>;
  onCancel?: () => void;
}

export function ModelForm({ model, locale, onSuccess, onCancel }: ModelFormProps) {
  const t = useTranslations();
  const router = useRouter();
  const createModel = useCreateModel();
  const updateModel = useUpdateModel();

  const { data: providersResponse } = useProviders({
    page_size: 100,
  });

  const form = useForm<ModelFormData>({
    resolver: zodResolver(modelFormSchema),
    defaultValues: model ? {
      name: model.model_identifier || '',
      display_name: model.model_name || '',
      provider_id: model.provider_id || '',
      organization_id: null,
      security_level: (model.security_level as 'secure' | 'sensitive' | 'insecure') || null,
      metadata: model.model_metadata || {},
    } : {
      name: '',
      display_name: '',
      provider_id: '',
      organization_id: null,
      security_level: null,
      metadata: {},
    },
  });

  const onSubmit = async (data: ModelFormData) => {
    try {
      if (model) {
        await updateModel.mutateAsync({
          id: model.id,
          data: {
            model_name: data.display_name,
            security_level: data.security_level,
            model_metadata: data.metadata,
          },
        });
        toast.success(t('models.updateSuccess'));
      } else {
        // For create, map form fields to CreateModelRequest
        await createModel.mutateAsync({
          provider_id: data.provider_id,
          model_name: data.display_name,
          model_identifier: data.name,
          context_length: 128000,  // Default context length
          max_generation_length: 8192,  // Default max generation
          model_metadata: data.metadata,
        });
        toast.success(t('models.createSuccess'));
      }
      // Call onSuccess callback if provided, otherwise navigate
      if (onSuccess) {
        await onSuccess();
      } else {
        router.push('/models');
      }
    } catch (error: any) {
      toast.error(error.message || t('errors.generic'));
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('models.fields.name')}</FormLabel>
              <FormControl>
                <Input {...field} placeholder={t('models.placeholders.name')} disabled={!!model} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="display_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('models.fields.displayName')}</FormLabel>
              <FormControl>
                <Input {...field} placeholder={t('models.placeholders.displayName')} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="provider_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('models.fields.providerId')}</FormLabel>
              <Select onValueChange={field.onChange} value={field.value} disabled={!!model}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder={t('models.fields.providerId')} />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {providersResponse?.items.map((provider) => (
                    <SelectItem key={provider.id} value={provider.id}>
                      {provider.name}
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
          name="security_level"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('models.fields.securityLevel')}</FormLabel>
              <Select
                onValueChange={(val) => field.onChange(val === 'none' ? null : val)}
                value={field.value || 'none'}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder={t('models.placeholders.securityLevel')} />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="none">-</SelectItem>
                  <SelectItem value="secure">{t('models.securityLevels.secure')}</SelectItem>
                  <SelectItem value="sensitive">{t('models.securityLevels.sensitive')}</SelectItem>
                  <SelectItem value="insecure">{t('models.securityLevels.insecure')}</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={onCancel || (() => router.push('/models'))}
          >
            {t('common.cancel')}
          </Button>
          <Button type="submit" disabled={createModel.isPending || updateModel.isPending}>
            {model ? t('common.update') : t('common.create')}
          </Button>
        </div>
      </form>
    </Form>
  );
}
