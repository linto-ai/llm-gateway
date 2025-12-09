'use client';

import { useEffect, useMemo } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslations, useLocale } from 'next-intl';

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
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { ChevronDown, Info } from 'lucide-react';

import { FlavorConfigAdvanced } from './FlavorConfigAdvanced';
import { FailoverChainPreview } from './FailoverChainPreview';
import { usePrompts } from '@/hooks/use-prompts';
import { SUPPORTED_LANGUAGES } from '@/lib/constants';
import type { FlavorFormData } from '@/schemas/forms';
import type { ServiceResponse, FlavorResponse } from '@/types/service';
import type { ServiceTypeConfig } from '@/types/service-type';

interface FlavorWizardAdvancedProps {
  service: ServiceResponse;
  config?: ServiceTypeConfig;
  flavor?: FlavorResponse;
}

export function FlavorWizardAdvanced({ service, config, flavor }: FlavorWizardAdvancedProps) {
  const t = useTranslations('services.flavors');
  const tFlavors = useTranslations('flavors');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const form = useFormContext<FlavorFormData>();

  // Extract stable references from react-hook-form to avoid infinite loops
  const { setValue, getValues } = form;

  const outputType = form.watch('output_type');
  const failoverEnabled = form.watch('failover_enabled');

  // Only show extraction prompt config when output type is markdown
  const showExtractionConfig = outputType === 'markdown';

  // Fetch prompts for extraction and categorization prompt selectors
  const { data: promptsResponse } = usePrompts({});
  const prompts = promptsResponse?.items || [];

  // Get failover flavor options from current service only
  // (failover should stay within the same service, just use a different flavor)
  const sameServiceFlavors = useMemo(() => {
    if (!service?.flavors) return [];
    return service.flavors.map(f => ({
      ...f,
      service_name: service.name,
      service_id: service.id,
    }));
  }, [service]);

  return (
    <div className="space-y-6">
      {/* Task Priority */}
      <FormField
        control={form.control}
        name="priority"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('taskPriority')}</FormLabel>
            <Select
              onValueChange={(value) => field.onChange(parseInt(value))}
              value={String(field.value ?? 5)}
            >
              <FormControl>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem value="0">{t('priorityOptions.0')}</SelectItem>
                <SelectItem value="1">{t('priorityOptions.1')}</SelectItem>
                <SelectItem value="2">{t('priorityOptions.2')}</SelectItem>
                <SelectItem value="3">{t('priorityOptions.3')}</SelectItem>
                <SelectItem value="4">{t('priorityOptions.4')}</SelectItem>
                <SelectItem value="5">{t('priorityOptions.5')}</SelectItem>
                <SelectItem value="6">{t('priorityOptions.6')}</SelectItem>
                <SelectItem value="7">{t('priorityOptions.7')}</SelectItem>
                <SelectItem value="8">{t('priorityOptions.8')}</SelectItem>
                <SelectItem value="9">{t('priorityOptions.9')}</SelectItem>
              </SelectContent>
            </Select>
            <FormDescription>{t('taskPriorityDescription')}</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Output Type */}
      <FormField
        control={form.control}
        name="output_type"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('fields.outputType')}</FormLabel>
            <Select onValueChange={field.onChange} value={field.value || 'text'}>
              <FormControl>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem value="text">
                  <div className="flex flex-col">
                    <span>{t('outputTypes.text')}</span>
                    <span className="text-xs text-muted-foreground">{t('outputTypeHints.text')}</span>
                  </div>
                </SelectItem>
                <SelectItem value="markdown">
                  <div className="flex flex-col">
                    <span>{t('outputTypes.markdown')}</span>
                    <span className="text-xs text-muted-foreground">{t('outputTypeHints.markdown')}</span>
                  </div>
                </SelectItem>
                <SelectItem value="json">
                  <div className="flex flex-col">
                    <span>{t('outputTypes.json')}</span>
                    <span className="text-xs text-muted-foreground">{t('outputTypeHints.json')}</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <FormDescription>{t('descriptions.outputType')}</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Frequency Penalty Slider */}
      <FormField
        control={form.control}
        name="frequency_penalty"
        render={({ field }) => (
          <FormItem>
            <FormLabel>
              {t('fields.frequencyPenalty')}: {field.value}
            </FormLabel>
            <FormControl>
              <Slider
                min={0}
                max={2}
                step={0.1}
                value={[field.value]}
                onValueChange={([value]) => field.onChange(value)}
              />
            </FormControl>
            <FormDescription>{t('descriptions.frequencyPenalty')}</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Presence Penalty Slider */}
      <FormField
        control={form.control}
        name="presence_penalty"
        render={({ field }) => (
          <FormItem>
            <FormLabel>
              {t('fields.presencePenalty')}: {field.value}
            </FormLabel>
            <FormControl>
              <Slider
                min={0}
                max={2}
                step={0.1}
                value={[field.value]}
                onValueChange={([value]) => field.onChange(value)}
              />
            </FormControl>
            <FormDescription>{t('descriptions.presencePenalty')}</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Estimated Cost per 1K Tokens */}
      <FormField
        control={form.control}
        name="estimated_cost_per_1k_tokens"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('fields.estimatedCost')}</FormLabel>
            <FormControl>
              <Input
                type="text"
                inputMode="decimal"
                placeholder="0.0001"
                name={field.name}
                ref={field.ref}
                value={field.value ?? ''}
                onChange={(e) => {
                  const val = e.target.value;
                  // Only allow valid decimal patterns
                  if (val === '' || /^[0-9]*\.?[0-9]*$/.test(val)) {
                    // Keep as string during typing to preserve "0.", "0.0", etc.
                    field.onChange(val === '' ? undefined : val);
                  }
                }}
                onBlur={(e) => {
                  const val = e.target.value;
                  // Convert to number only on blur
                  if (val === '') {
                    field.onChange(undefined);
                  } else {
                    const num = parseFloat(val);
                    if (!isNaN(num)) {
                      field.onChange(num);
                    }
                  }
                  field.onBlur();
                }}
              />
            </FormControl>
            <FormDescription>{t('descriptions.estimatedCost')}</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Max Concurrent Requests */}
      <FormField
        control={form.control}
        name="max_concurrent_requests"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('fields.maxConcurrentRequests')}</FormLabel>
            <FormControl>
              <Input
                type="number"
                min={1}
                {...field}
                value={field.value || ''}
                onChange={(e) =>
                  field.onChange(e.target.value ? parseInt(e.target.value) : undefined)
                }
              />
            </FormControl>
            <FormDescription>{t('descriptions.maxConcurrentRequests')}</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Advanced Configuration - Stop Sequences & Custom Params */}
      <Collapsible className="border rounded-lg p-4">
        <CollapsibleTrigger asChild>
          <Button type="button" variant="ghost" className="w-full justify-between p-0">
            <h3 className="text-sm font-medium">{t('advancedSettings')}</h3>
            <ChevronDown className="h-4 w-4" />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-4">
          <FlavorConfigAdvanced
            stopSequences={form.watch('stop_sequences')}
            customParams={form.watch('custom_params')}
            onStopSequencesChange={(sequences) => form.setValue('stop_sequences', sequences)}
            onCustomParamsChange={(params) => form.setValue('custom_params', params)}
          />
        </CollapsibleContent>
      </Collapsible>

      {/* Placeholder Extraction Configuration - only shown for markdown output (document generation) */}
      {showExtractionConfig && (
        <Collapsible className="border rounded-lg p-4">
          <CollapsibleTrigger asChild>
            <Button type="button" variant="ghost" className="w-full justify-between p-0">
              <h3 className="text-sm font-medium">{tFlavors('placeholderExtraction.title')}</h3>
              <ChevronDown className="h-4 w-4" />
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-4 space-y-4">
            <p className="text-sm text-muted-foreground">
              {tFlavors('placeholderExtraction.description')}
            </p>

            {/* Placeholder Extraction Prompt */}
            <FormField
              control={form.control}
              name="placeholder_extraction_prompt_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{tFlavors('placeholderExtraction.prompt')}</FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(value === 'none' ? undefined : value)}
                    value={field.value || 'none'}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="none">{tCommon('none')}</SelectItem>
                      {prompts
                        .filter((p) =>
                          // Prefer prompts with 'field_extraction' prompt type, or fallback to name matching
                          p.prompt_type?.code === 'field_extraction' ||
                          p.name.toLowerCase().includes('extract') ||
                          p.name.toLowerCase().includes('placeholder')
                        )
                        .map((prompt) => (
                          <SelectItem key={prompt.id} value={prompt.id}>
                            {prompt.name}
                            {prompt.prompt_type?.code === 'field_extraction' && (
                              <span className="ml-1 text-xs text-muted-foreground">[extraction]</span>
                            )}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>{tFlavors('placeholderExtraction.promptHelp')}</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Categorization Configuration */}
      <Collapsible className="border rounded-lg p-4">
        <CollapsibleTrigger asChild>
          <Button type="button" variant="ghost" className="w-full justify-between p-0">
            <h3 className="text-sm font-medium">{tFlavors('categorization.title')}</h3>
            <ChevronDown className="h-4 w-4" />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-4 space-y-4">
          <p className="text-sm text-muted-foreground">
            {tFlavors('categorization.description')}
          </p>

          {/* Categorization Prompt */}
          <FormField
            control={form.control}
            name="categorization_prompt_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{tFlavors('categorization.prompt')}</FormLabel>
                <Select
                  onValueChange={(value) => field.onChange(value === 'none' ? undefined : value)}
                  value={field.value || 'none'}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="none">{tCommon('none')}</SelectItem>
                    {prompts
                      .filter((p) =>
                        // Prefer prompts with 'categorization' service type
                        p.service_type === 'categorization' ||
                        p.name.toLowerCase().includes('categor') ||
                        p.name.toLowerCase().includes('tag') ||
                        p.name.toLowerCase().includes('classif')
                      )
                      .map((prompt) => (
                        <SelectItem key={prompt.id} value={prompt.id}>
                          {prompt.name}
                          {prompt.service_type === 'categorization' && (
                            <span className="ml-1 text-xs text-muted-foreground">[categorization]</span>
                          )}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <FormDescription>{tFlavors('categorization.promptHelp')}</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </CollapsibleContent>
      </Collapsible>

      {/* Failover Configuration Section */}
      <div className="border-t pt-4 mt-4">
        <h3 className="text-sm font-medium mb-2">{t('failoverConfig.title')}</h3>
        <p className="text-xs text-muted-foreground mb-4">
          {t('failoverConfig.description')}
        </p>

        {/* Enable Failover Toggle */}
        <FormField
          control={form.control}
          name="failover_enabled"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 mb-4">
              <div className="space-y-0.5">
                <FormLabel>{t('failoverConfig.enable')}</FormLabel>
                <FormDescription className="text-xs">
                  {t('failoverConfig.enableDescription')}
                </FormDescription>
              </div>
              <FormControl>
                <Switch checked={field.value} onCheckedChange={field.onChange} />
              </FormControl>
            </FormItem>
          )}
        />

        {failoverEnabled && (
          <>
            {/* Failover Flavor Selector */}
            <FormField
              control={form.control}
              name="failover_flavor_id"
              render={({ field }) => (
                <FormItem className="mb-4">
                  <FormLabel>{t('failoverConfig.flavorLabel')}</FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(value === 'none' ? undefined : value)}
                    value={field.value || 'none'}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t('failoverConfig.flavorPlaceholder')} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="none">{tCommon('none')}</SelectItem>
                      {sameServiceFlavors
                        .filter(f => f.id !== flavor?.id && f.is_active)
                        .map((f) => (
                          <SelectItem key={f.id} value={f.id}>
                            {f.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Failover Chain Preview */}
            {flavor?.id && (
              <FailoverChainPreview serviceId={service.id} flavorId={flavor.id} />
            )}

            {/* Failover Triggers */}
            <div className="space-y-3 mt-4">
              <Label className="text-sm font-medium">{t('failoverConfig.triggers')}</Label>
              <div className="grid grid-cols-2 gap-3">
                <FormField
                  control={form.control}
                  name="failover_on_timeout"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2">
                      <FormControl>
                        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                      <FormLabel className="text-sm font-normal">
                        {t('failoverConfig.onTimeout')}
                      </FormLabel>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="failover_on_rate_limit"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2">
                      <FormControl>
                        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                      <FormLabel className="text-sm font-normal">
                        {t('failoverConfig.onRateLimit')}
                      </FormLabel>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="failover_on_model_error"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2">
                      <FormControl>
                        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                      <FormLabel className="text-sm font-normal">
                        {t('failoverConfig.onModelError')}
                      </FormLabel>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="failover_on_content_filter"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2">
                      <FormControl>
                        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                      <FormLabel className="text-sm font-normal">
                        {t('failoverConfig.onContentFilter')}
                      </FormLabel>
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Max Failover Depth */}
            <FormField
              control={form.control}
              name="max_failover_depth"
              render={({ field }) => (
                <FormItem className="mt-4">
                  <FormLabel>{t('failoverConfig.maxDepth')}</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      {...field}
                      onChange={(e) => field.onChange(parseInt(e.target.value) || 3)}
                    />
                  </FormControl>
                  <FormDescription className="text-xs">
                    {t('failoverConfig.maxDepthDescription')}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Info Box: Failover vs Fallback */}
            <Alert className="mt-4">
              <Info className="h-4 w-4" />
              <AlertDescription className="text-xs">
                {t('failoverConfig.vsFallback')}
              </AlertDescription>
            </Alert>
          </>
        )}
      </div>
    </div>
  );
}
