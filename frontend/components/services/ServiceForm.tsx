'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations, useLocale } from 'next-intl';

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
import { Textarea } from '@/components/ui/textarea';

import { useCreateService, useUpdateService } from '@/hooks/use-services';
import { useServiceTypes } from '@/hooks/use-service-types';
import { serviceFormSchema, type ServiceFormData } from '@/schemas/forms';
import type { ServiceResponse, CreateServiceRequest, CreateFlavorRequest } from '@/types/service';

interface ServiceFormProps {
  service?: ServiceResponse;
  onSuccess: () => void;
  onCancel: () => void;
}

export function ServiceForm({ service, onSuccess, onCancel }: ServiceFormProps) {
  const t = useTranslations('services');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  const createMutation = useCreateService();
  const updateMutation = useUpdateService();
  const { data: serviceTypes } = useServiceTypes();

  const form = useForm<ServiceFormData>({
    resolver: zodResolver(serviceFormSchema),
    defaultValues: {
      name: service?.name || '',
      service_type: service?.service_type || 'summary',
      description: {
        en: service?.description.en || '',
        fr: service?.description.fr || '',
      },
      organization_id: service?.organization_id || null,
      // Don't load flavors in edit mode - they are managed separately via Flavors tab
      flavors: [],
    },
  });

  const onSubmit = async (data: ServiceFormData) => {
    try {
      if (service) {
        // Update existing service
        await updateMutation.mutateAsync({
          id: service.id,
          data: {
            name: data.name,
            description: data.description,
            organization_id: data.organization_id || '',
          },
        });
      } else {
        // Create new service with initial flavors
        // Clean up null values to undefined for API compatibility
        const cleanedFlavors = (data.flavors || []).map(f => ({
          ...f,
          estimated_cost_per_1k_tokens: f.estimated_cost_per_1k_tokens ?? undefined,
          max_concurrent_requests: f.max_concurrent_requests ?? undefined,
          create_new_turn_after: f.create_new_turn_after ?? undefined,
          max_new_turns: f.max_new_turns ?? undefined,
          summary_turns: f.summary_turns ?? undefined,
          system_prompt_id: f.system_prompt_id ?? undefined,
          user_prompt_template_id: f.user_prompt_template_id ?? undefined,
          reduce_prompt_id: f.reduce_prompt_id ?? undefined,
          tokenizer_override: f.tokenizer_override ?? undefined,
          placeholder_extraction_prompt_id: f.placeholder_extraction_prompt_id ?? undefined,
          fallback_flavor_id: f.fallback_flavor_id ?? undefined,
          categorization_prompt_id: f.categorization_prompt_id ?? undefined,
        }));

        const createPayload: CreateServiceRequest = {
          name: data.name,
          service_type: data.service_type,
          description: data.description,
          organization_id: data.organization_id || '',
          flavors: cleanedFlavors as CreateFlavorRequest[],
        };

        await createMutation.mutateAsync(createPayload);
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

        {/* Service Type */}
        <FormField
          control={form.control}
          name="service_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.serviceType')}</FormLabel>
              <Select
                onValueChange={field.onChange}
                defaultValue={field.value}
                disabled={!!service} // Cannot change type after creation
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
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
              <FormLabel>
                {t('fields.descriptionEn')} <span className="text-muted-foreground text-xs">({tCommon('optional')})</span>
              </FormLabel>
              <FormControl>
                <Textarea
                  placeholder={t('placeholders.descriptionEn')}
                  rows={3}
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
              <FormLabel>
                {t('fields.descriptionFr')} <span className="text-muted-foreground text-xs">({tCommon('optional')})</span>
              </FormLabel>
              <FormControl>
                <Textarea
                  placeholder={t('placeholders.descriptionFr')}
                  rows={3}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Organization ID */}
        <FormField
          control={form.control}
          name="organization_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                {t('fields.organizationId')} <span className="text-muted-foreground text-xs">({tCommon('optional')})</span>
              </FormLabel>
              <FormControl>
                <Input
                  placeholder={t('placeholders.organizationId')}
                  {...field}
                  value={field.value || ''}
                  onChange={(e) => field.onChange(e.target.value || null)}
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
            {service ? tCommon('update') : tCommon('create')}
          </Button>
        </div>
      </form>
    </Form>
  );
}
