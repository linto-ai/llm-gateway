'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
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
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';

import { useCreateProvider, useUpdateProvider } from '@/hooks/use-providers';
import { providerFormSchema, type ProviderFormData } from '@/schemas/forms';
import { PROVIDER_TYPES, SECURITY_LEVELS, SECURITY_LEVEL_LABELS } from '@/lib/constants';
import type { ProviderResponse } from '@/types/provider';

interface ProviderFormProps {
  provider?: ProviderResponse;
  onSuccess: () => void;
  onCancel: () => void;
}

export function ProviderForm({ provider, onSuccess, onCancel }: ProviderFormProps) {
  const t = useTranslations('providers');
  const tCommon = useTranslations('common');
  const tValidation = useTranslations('validation');

  const createMutation = useCreateProvider();
  const updateMutation = useUpdateProvider();

  // Create a custom schema that validates api_key only on creation
  const dynamicSchema = providerFormSchema.refine(
    (data) => {
      // If we're updating (provider exists) and api_key is empty, that's OK
      if (provider && !data.api_key) {
        return true;
      }
      // If we're creating, api_key must be provided
      if (!provider && (!data.api_key || data.api_key.length === 0)) {
        return false;
      }
      return true;
    },
    {
      message: 'validation.required',
      path: ['api_key'],
    }
  );

  const form = useForm<ProviderFormData>({
    resolver: zodResolver(dynamicSchema),
    defaultValues: {
      name: provider?.name || '',
      provider_type: provider?.provider_type || 'openai',
      api_base_url: provider?.api_base_url || '',
      api_key: '', // Never pre-fill API key for security
      security_level: provider?.security_level ?? 1, // Default to Medium (1)
      metadata: provider?.metadata || {},
    },
  });

  const onSubmit = async (data: ProviderFormData) => {
    try {
      if (provider) {
        // Update existing provider
        await updateMutation.mutateAsync({
          id: provider.id,
          data: {
            name: data.name,
            provider_type: data.provider_type,
            api_base_url: data.api_base_url,
            api_key: data.api_key || undefined, // Only send if changed
            security_level: data.security_level,
            metadata: data.metadata,
          },
        });
      } else {
        // Create new provider - api_key is required for new providers
        await createMutation.mutateAsync({
          name: data.name,
          provider_type: data.provider_type,
          api_base_url: data.api_base_url,
          api_key: data.api_key || '',
          security_level: data.security_level,
          metadata: data.metadata,
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
                <Input placeholder={t('placeholders.name')} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Provider Type */}
        <FormField
          control={form.control}
          name="provider_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.providerType')}</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {PROVIDER_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {t(`types.${type}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* API Base URL */}
        <FormField
          control={form.control}
          name="api_base_url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.apiBaseUrl')}</FormLabel>
              <FormControl>
                <Input type="url" placeholder={t('placeholders.apiBaseUrl')} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* API Key */}
        <FormField
          control={form.control}
          name="api_key"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                {t('fields.apiKey')}
                {provider && <span className="text-xs text-muted-foreground ml-2">(leave empty to keep current)</span>}
              </FormLabel>
              <FormControl>
                <Input type="password" placeholder={t('placeholders.apiKey')} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Security Level */}
        <FormField
          control={form.control}
          name="security_level"
          render={({ field }) => (
            <FormItem className="space-y-3">
              <FormLabel>{t('fields.securityLevel')}</FormLabel>
              <FormControl>
                <RadioGroup
                  onValueChange={(val) => field.onChange(parseInt(val, 10))}
                  value={String(field.value)}
                  className="flex flex-col space-y-1"
                >
                  {SECURITY_LEVELS.map((level) => (
                    <FormItem key={level} className="flex items-center space-x-3 space-y-0">
                      <FormControl>
                        <RadioGroupItem value={String(level)} />
                      </FormControl>
                      <FormLabel className="font-normal">
                        {t(`securityLevels.${SECURITY_LEVEL_LABELS[level]}`)}
                      </FormLabel>
                    </FormItem>
                  ))}
                </RadioGroup>
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
            {provider ? tCommon('update') : tCommon('create')}
          </Button>
        </div>
      </form>
    </Form>
  );
}
