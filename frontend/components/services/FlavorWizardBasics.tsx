'use client';

import { useFormContext, useWatch } from 'react-hook-form';
import { useTranslations } from 'next-intl';
import { Info } from 'lucide-react';

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
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';

import { useModels } from '@/hooks/use-models';
import type { FlavorFormData } from '@/schemas/forms';
import { formatTokens, getEffectiveModelLimits } from '@/lib/utils';

export function FlavorWizardBasics() {
  const t = useTranslations('services.flavors');
  const tLimits = useTranslations('models.limits');
  const form = useFormContext<FlavorFormData>();

  // Watch model_id to show limits info
  const selectedModelId = useWatch({ control: form.control, name: 'model_id' });

  // Fetch models for selection
  const { data: modelsResponse } = useModels({});
  const models = modelsResponse?.items || [];

  // Find selected model to display limits
  const selectedModel = models.find(m => m.id === selectedModelId);

  // Get effective limits (with override support)
  const getModelLimits = (model: typeof selectedModel) => {
    if (!model) return null;
    return getEffectiveModelLimits(model);
  };

  return (
    <div className="space-y-6">
      {/* Flavor Name */}
      <FormField
        control={form.control}
        name="name"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('fields.name')} *</FormLabel>
            <FormControl>
              <Input {...field} placeholder={t('placeholders.flavorName')} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Model Selection */}
      <FormField
        control={form.control}
        name="model_id"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('fields.modelId')} *</FormLabel>
            <Select onValueChange={field.onChange} value={field.value}>
              <FormControl>
                <SelectTrigger>
                  <SelectValue placeholder={t('placeholders.selectModel')} />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                {models.map((model) => {
                  const limits = getEffectiveModelLimits(model);
                  return (
                    <SelectItem key={model.id} value={model.id}>
                      <div className="flex items-center gap-2">
                        <span>{model.model_name}</span>
                        <span className="text-xs text-muted-foreground">
                          ({formatTokens(limits.contextLength)} ctx)
                        </span>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Model Limits Info (when model selected) */}
      {selectedModel && (() => {
        const limits = getEffectiveModelLimits(selectedModel);
        return (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <div className="flex flex-wrap gap-4 text-sm">
                <div>
                  <span className="font-medium">{tLimits('contextLength')}:</span>{' '}
                  {formatTokens(limits.contextLength)} tokens
                </div>
                <div>
                  <span className="font-medium">{tLimits('maxGeneration')}:</span>{' '}
                  {formatTokens(limits.maxGeneration)} tokens
                </div>
              </div>
            </AlertDescription>
          </Alert>
        );
      })()}

      {/* Description */}
      <FormField
        control={form.control}
        name="description"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('fields.description')}</FormLabel>
            <FormControl>
              <Input {...field} placeholder={t('placeholders.description')} />
            </FormControl>
            <FormDescription>{t('descriptions.description')}</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Is Default */}
      <FormField
        control={form.control}
        name="is_default"
        render={({ field }) => (
          <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
            <FormControl>
              <Checkbox checked={field.value} onCheckedChange={field.onChange} />
            </FormControl>
            <div className="space-y-1 leading-none">
              <FormLabel>{t('fields.isDefault')}</FormLabel>
            </div>
          </FormItem>
        )}
      />

      {/* Is Active */}
      <FormField
        control={form.control}
        name="is_active"
        render={({ field }) => (
          <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
            <FormControl>
              <Checkbox checked={field.value} onCheckedChange={field.onChange} />
            </FormControl>
            <div className="space-y-1 leading-none">
              <FormLabel>{t('fields.isActive')}</FormLabel>
              <FormDescription>{t('descriptions.isActive')}</FormDescription>
            </div>
          </FormItem>
        )}
      />
    </div>
  );
}
