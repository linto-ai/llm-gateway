'use client';

import { useMemo } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslations } from 'next-intl';
import { Zap, RefreshCw } from 'lucide-react';

import {
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
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';

import { FlavorPresetSelector } from './FlavorPresetSelector';
import type { FlavorFormData } from '@/schemas/forms';
import type { ServiceResponse } from '@/types/service';
import type { ServiceTypeConfig } from '@/types/service-type';
import type { FlavorPresetConfig } from '@/types/preset';

interface FlavorWizardProcessingProps {
  service: ServiceResponse;
  config?: ServiceTypeConfig;
  currentFlavorId?: string;
}

export function FlavorWizardProcessing({ service, config, currentFlavorId }: FlavorWizardProcessingProps) {
  const t = useTranslations('services.flavors');
  const form = useFormContext<FlavorFormData>();

  // Only summary service type supports reduce; derive from config or service type
  const supportsReduce = config?.supports_reduce ?? (service.service_type === 'summary');
  const supportsChunking = config?.supports_chunking ?? true;
  const processingMode = form.watch('processing_mode');

  // Get fallback flavor options from current service only
  // Fallback should only use iterative flavors from the same service
  // (single_pass can fallback to iterative when content exceeds context)
  const fallbackFlavors = useMemo(() => {
    if (!service?.flavors) return [];
    return service.flavors
      .filter(f => f.processing_mode === 'iterative') // Only iterative flavors make sense as fallback
      .map(f => ({
        ...f,
        service_name: service.name,
        service_id: service.id,
      }));
  }, [service]);

  // Handler for preset selection
  const handlePresetSelect = (presetConfig: FlavorPresetConfig) => {
    if (presetConfig.processing_mode && (
      presetConfig.processing_mode !== 'iterative' || supportsChunking
    )) {
      form.setValue('processing_mode', presetConfig.processing_mode);
    }
    if (presetConfig.temperature !== undefined) {
      form.setValue('temperature', presetConfig.temperature);
    }
    if (presetConfig.top_p !== undefined) {
      form.setValue('top_p', presetConfig.top_p);
    }
    if (supportsChunking) {
      if (presetConfig.max_new_turns !== undefined && presetConfig.max_new_turns !== null) {
        form.setValue('max_new_turns', presetConfig.max_new_turns);
      }
      if (presetConfig.summary_turns !== undefined) {
        form.setValue('summary_turns', presetConfig.summary_turns);
      }
      if (presetConfig.create_new_turn_after !== undefined) {
        form.setValue('create_new_turn_after', presetConfig.create_new_turn_after);
      }
    }
    if (supportsReduce && presetConfig.reduce_summary !== undefined) {
      form.setValue('reduce_summary', presetConfig.reduce_summary);
    }
  };

  return (
    <div className="space-y-6">
      {/* Preset Selector */}
      {(supportsReduce || supportsChunking) && (
        <FlavorPresetSelector
          serviceType={service.service_type}
          onSelect={handlePresetSelect}
        />
      )}

      {/* Processing Mode Select */}
      {(supportsReduce || supportsChunking) && (
        <FormField
          control={form.control}
          name="processing_mode"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('processingMode.label')}</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="single_pass">
                    <div className="flex items-center gap-2">
                      <Zap className="h-4 w-4" />
                      {t('processingMode.singlePass')}
                    </div>
                  </SelectItem>
                  {supportsChunking && (
                    <SelectItem value="iterative">
                      <div className="flex items-center gap-2">
                        <RefreshCw className="h-4 w-4" />
                        {t('processingMode.iterative')}
                      </div>
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
              <FormDescription>
                {t(`processingMode.description.${field.value}`)}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
      )}

      {/* Fallback Flavor selector (only for single_pass) */}
      {processingMode === 'single_pass' && (
        <FormField
          control={form.control}
          name="fallback_flavor_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fallbackFlavor.label')}</FormLabel>
              <Select
                onValueChange={(value) => field.onChange(value === 'none' ? undefined : value)}
                value={field.value || 'none'}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder={t('fallbackFlavor.placeholder')} />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="none">
                    {t('fallbackFlavor.none')}
                  </SelectItem>
                  {fallbackFlavors
                    .filter(f => f.id !== currentFlavorId && f.is_active)
                    .map((f) => (
                      <SelectItem key={f.id} value={f.id}>
                        {f.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <FormDescription>
                {t('fallbackFlavor.description')}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
      )}

      {/* Temperature Slider */}
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
                onValueChange={([value]) => field.onChange(value)}
              />
            </FormControl>
            <FormDescription>0.0 - 2.0</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Top P Slider */}
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
                onValueChange={([value]) => field.onChange(value)}
              />
            </FormControl>
            <FormDescription>0.0 - 1.0</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Chunking Parameters - Only shown for iterative mode */}
      {supportsChunking && processingMode === 'iterative' && (
        <div className="border-t pt-4 mt-4 space-y-4">
          <h4 className="text-sm font-medium">{t('chunking.title')}</h4>

          {/* Create New Turn After (tokens) */}
          <FormField
            control={form.control}
            name="create_new_turn_after"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('chunking.createNewTurnAfter')}</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={1}
                    step={100}
                    placeholder="100"
                    value={field.value ?? ''}
                    onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                  />
                </FormControl>
                <FormDescription>{t('chunking.createNewTurnAfterDesc')}</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Max New Turns per batch */}
          <FormField
            control={form.control}
            name="max_new_turns"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('chunking.maxNewTurns')}</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={1}
                    placeholder="10"
                    value={field.value ?? ''}
                    onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                  />
                </FormControl>
                <FormDescription>{t('chunking.maxNewTurnsDesc')}</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Summary Turns to keep */}
          <FormField
            control={form.control}
            name="summary_turns"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('chunking.summaryTurns')}</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={1}
                    placeholder="5"
                    value={field.value ?? ''}
                    onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                  />
                </FormControl>
                <FormDescription>{t('chunking.summaryTurnsDesc')}</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Reduce Summary toggle */}
          {supportsReduce && (
            <FormField
              control={form.control}
              name="reduce_summary"
              render={({ field }) => (
                <FormItem className="flex items-center gap-3 rounded-md border p-4">
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                  <div className="space-y-1">
                    <FormLabel>{t('chunking.reduceSummary')}</FormLabel>
                    <FormDescription>{t('chunking.reduceSummaryDesc')}</FormDescription>
                  </div>
                </FormItem>
              )}
            />
          )}

          {/* Consolidate Summary toggle */}
          <FormField
            control={form.control}
            name="consolidate_summary"
            render={({ field }) => (
              <FormItem className="flex items-center gap-3 rounded-md border p-4">
                <FormControl>
                  <Switch
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
                <div className="space-y-1">
                  <FormLabel>{t('chunking.consolidateSummary')}</FormLabel>
                  <FormDescription>{t('chunking.consolidateSummaryDesc')}</FormDescription>
                </div>
              </FormItem>
            )}
          />
        </div>
      )}
    </div>
  );
}
