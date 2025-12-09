'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';
import { z } from 'zod';

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
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { useCreatePreset, useUpdatePreset } from '@/hooks/use-presets';
import { useServiceTypes } from '@/hooks/use-service-types';
import { useLocale } from 'next-intl';
import type { FlavorPreset, FlavorPresetConfig } from '@/types/preset';

const presetFormSchema = z.object({
  name: z.string().min(1).max(100),
  service_type: z.string().default('summary'),
  description_en: z.string().optional(),
  description_fr: z.string().optional(),
  processing_mode: z.enum(['single_pass', 'iterative']),
  temperature: z.number().min(0).max(2),
  top_p: z.number().min(0).max(1),
  // Iterative processing fields - nullable for single_pass mode
  max_new_turns: z.number().int().min(1).max(50).nullable().optional(),
  summary_turns: z.number().int().min(0).max(20).nullable().optional(),
  create_new_turn_after: z.number().int().min(100).max(10000).nullable().optional(),
  reduce_summary: z.boolean().optional(),
});

type PresetFormData = z.infer<typeof presetFormSchema>;

interface PresetFormProps {
  preset?: FlavorPreset;
  onSuccess: () => void;
  onCancel: () => void;
}

export function PresetForm({ preset, onSuccess, onCancel }: PresetFormProps) {
  const t = useTranslations('presets');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  const createMutation = useCreatePreset();
  const updateMutation = useUpdatePreset();
  const { data: serviceTypes } = useServiceTypes();

  const form = useForm<PresetFormData>({
    resolver: zodResolver(presetFormSchema),
    defaultValues: {
      name: preset?.name || '',
      service_type: preset?.service_type || 'summary',
      description_en: preset?.description_en || '',
      description_fr: preset?.description_fr || '',
      processing_mode: preset?.config.processing_mode || 'iterative',
      temperature: preset?.config.temperature ?? 0.7,
      top_p: preset?.config.top_p ?? 0.9,
      max_new_turns: preset?.config.max_new_turns || null,
      summary_turns: preset?.config.summary_turns ?? 5,
      create_new_turn_after: preset?.config.create_new_turn_after ?? 100,
      reduce_summary: preset?.config.reduce_summary ?? false,
    },
  });

  const onSubmit = async (data: PresetFormData) => {
    const isIterative = data.processing_mode === 'iterative';

    const config: FlavorPresetConfig = {
      processing_mode: data.processing_mode,
      temperature: data.temperature,
      top_p: data.top_p,
      // Iterative-specific fields - set defaults based on mode
      max_new_turns: isIterative ? (data.max_new_turns ?? 10) : null,
      summary_turns: isIterative ? (data.summary_turns ?? 5) : 0,
      create_new_turn_after: isIterative ? (data.create_new_turn_after ?? 3000) : 0,
      reduce_summary: isIterative ? (data.reduce_summary ?? false) : false,
    };

    if (preset) {
      await updateMutation.mutateAsync({
        presetId: preset.id,
        data: {
          name: data.name,
          description_en: data.description_en,
          description_fr: data.description_fr,
          config,
        },
      });
    } else {
      await createMutation.mutateAsync({
        name: data.name,
        service_type: data.service_type,
        description_en: data.description_en,
        description_fr: data.description_fr,
        config,
      });
    }
    onSuccess();
  };

  // Watch processing mode and service type to conditionally show fields
  const processingMode = form.watch('processing_mode');
  const serviceType = form.watch('service_type');
  const showIterativeFields = processingMode === 'iterative';

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.name')}</FormLabel>
              <FormControl>
                <Input {...field} disabled={preset?.is_system} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {!preset && (
          <FormField
            control={form.control}
            name="service_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('fields.serviceType')}</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
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
        )}

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="description_en"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('fields.descriptionEn')}</FormLabel>
                <FormControl>
                  <Textarea {...field} rows={2} />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="description_fr"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('fields.descriptionFr')}</FormLabel>
                <FormControl>
                  <Textarea {...field} rows={2} />
                </FormControl>
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="processing_mode"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.processingMode')}</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="single_pass">{t('modes.singlePass')}</SelectItem>
                  <SelectItem value="iterative">{t('modes.iterative')}</SelectItem>
                </SelectContent>
              </Select>
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="temperature"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('fields.temperature')}: {field.value}</FormLabel>
                <FormControl>
                  <Slider
                    min={0}
                    max={2}
                    step={0.1}
                    value={[field.value]}
                    onValueChange={([v]) => field.onChange(v)}
                  />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="top_p"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('fields.topP')}: {field.value}</FormLabel>
                <FormControl>
                  <Slider
                    min={0}
                    max={1}
                    step={0.05}
                    value={[field.value]}
                    onValueChange={([v]) => field.onChange(v)}
                  />
                </FormControl>
              </FormItem>
            )}
          />
        </div>

        {/* Iterative processing fields - only shown for iterative mode */}
        {showIterativeFields && (
          <>
            <div className="grid grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="create_new_turn_after"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('fields.createNewTurnAfter')}</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        value={field.value ?? 3000}
                        onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : null)}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                        disabled={field.disabled}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="max_new_turns"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('fields.maxNewTurns')}</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        value={field.value ?? 10}
                        onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : null)}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="summary_turns"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('fields.summaryTurns')}</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        value={field.value ?? 5}
                        onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : null)}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                        disabled={field.disabled}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>

            {/* Only show reduce_summary for summary service type */}
            {serviceType === 'summary' && (
              <FormField
                control={form.control}
                name="reduce_summary"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-2">
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                    <FormLabel className="!mt-0">{t('fields.reduceSummary')}</FormLabel>
                  </FormItem>
                )}
              />
            )}
          </>
        )}

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="outline" onClick={onCancel}>
            {tCommon('cancel')}
          </Button>
          <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
            {preset ? tCommon('update') : tCommon('create')}
          </Button>
        </div>
      </form>
    </Form>
  );
}
