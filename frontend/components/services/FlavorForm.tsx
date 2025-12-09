'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations, useLocale } from 'next-intl';
import { useEffect, useState, useMemo } from 'react';

import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { Badge } from '@/components/ui/badge';

import { useAddFlavor, useUpdateFlavor, useServices } from '@/hooks/use-services';
import { useModels } from '@/hooks/use-models';
import { usePrompts, useCreatePrompt } from '@/hooks/use-prompts';
import { useServiceTypeConfig } from '@/hooks/use-service-types';
import { flavorFormSchema, type FlavorFormData } from '@/schemas/forms';
import { SUPPORTED_LANGUAGES } from '@/lib/constants';
import { validatePromptForMode, type PromptValidationResult } from '@/lib/prompt-validation';
import type { FlavorResponse, ServiceResponse, OutputType } from '@/types/service';
import { FlavorPromptEditor } from './FlavorPromptEditor';
import { TemplateBrowserDialog } from './TemplateBrowserDialog';
import { SaveTemplateDialog } from './SaveTemplateDialog';
import { FlavorConfigAdvanced } from './FlavorConfigAdvanced';
import { FlavorPresetSelector } from './FlavorPresetSelector';
import { PromptSelector } from './PromptSelector';
import { FailoverChainPreview } from './FailoverChainPreview';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ChevronDown, Zap, RefreshCw, Info, AlertCircle } from 'lucide-react';
import { formatTokens, getEffectiveModelLimits } from '@/lib/utils';

// Helper to normalize legacy output_type values to canonical values
function normalizeOutputType(value: string | undefined): OutputType {
  const canonical: OutputType[] = ['text', 'markdown', 'json'];
  if (value && canonical.includes(value as OutputType)) {
    return value as OutputType;
  }
  // Map legacy values to canonical (including 'structured' -> 'markdown')
  if (value === 'abstractive' || value === 'extractive') {
    return 'text';
  }
  if (value === 'structured') {
    return 'markdown';
  }
  return 'text';
}

interface FlavorFormProps {
  service: ServiceResponse;
  flavor?: FlavorResponse;
  onSuccess: () => void;
  onCancel: () => void;
}

export function FlavorForm({ service, flavor, onSuccess, onCancel }: FlavorFormProps) {
  const t = useTranslations('services.flavors');
  const tFlavors = useTranslations('flavors');
  const tCommon = useTranslations('common');
  const tLimits = useTranslations('models.limits');
  const locale = useLocale();

  // Fetch service type configuration
  const { data: serviceTypeConfig, isLoading: configLoading } = useServiceTypeConfig(service?.service_type);

  // State for dialogs
  const [templateBrowserOpen, setTemplateBrowserOpen] = useState(false);
  const [saveTemplateDialogOpen, setSaveTemplateDialogOpen] = useState(false);
  const [activePromptType, setActivePromptType] = useState<'system' | 'user' | 'reduce'>('system');

  // Fetch models for selection
  const { data: modelsResponse } = useModels({});
  const models = modelsResponse?.items || [];

  // Fetch prompts for selection
  const { data: promptsResponse } = usePrompts({});
  const prompts = promptsResponse?.items || [];

  // Fetch all services to build fallback flavor options
  const { data: allServicesResponse } = useServices({});
  const allFlavors = useMemo(() => {
    if (!allServicesResponse?.items) return [];
    return allServicesResponse.items.flatMap(s =>
      s.flavors.map(f => ({
        ...f,
        service_name: s.name,
        service_id: s.id,
      }))
    );
  }, [allServicesResponse?.items]);

  const addFlavorMutation = useAddFlavor();
  const updateFlavorMutation = useUpdateFlavor();
  const createPromptMutation = useCreatePrompt();

  const form = useForm<FlavorFormData>({
    resolver: zodResolver(flavorFormSchema),
    defaultValues: {
      name: flavor?.name || '',
      model_id: flavor?.model_id || '',
      description: flavor?.description || '',
      is_default: flavor?.is_default || false,
      is_active: flavor?.is_active ?? true,
      temperature: flavor?.temperature || 0.7,
      top_p: flavor?.top_p || 0.9,
      frequency_penalty: flavor?.frequency_penalty || 0.0,
      presence_penalty: flavor?.presence_penalty || 0.0,
      stop_sequences: flavor?.stop_sequences || [],
      custom_params: flavor?.custom_params || {},
      estimated_cost_per_1k_tokens: flavor?.estimated_cost_per_1k_tokens || undefined,
      max_concurrent_requests: flavor?.max_concurrent_requests || undefined,
      priority: flavor?.priority || 0,
      output_type: normalizeOutputType(flavor?.output_type),
      system_prompt_id: flavor?.system_prompt_id || undefined,
      user_prompt_template_id: flavor?.user_prompt_template_id || undefined,
      reduce_prompt_id: flavor?.reduce_prompt_id || undefined,
      prompt_system_content: flavor?.prompt_system_content || '',
      prompt_user_content: flavor?.prompt_user_content || '',
      prompt_reduce_content: flavor?.prompt_reduce_content || '',
      // Placeholder extraction configuration
      placeholder_extraction_prompt_id: flavor?.placeholder_extraction_prompt_id || undefined,
      // Processing mode
      processing_mode: flavor?.processing_mode || 'iterative',
      // Fallback configuration
      fallback_flavor_id: flavor?.fallback_flavor_id || undefined,
      // Chunking parameters
      create_new_turn_after: flavor?.create_new_turn_after ?? undefined,
      max_new_turns: flavor?.max_new_turns ?? undefined,
      summary_turns: flavor?.summary_turns ?? undefined,
      reduce_summary: flavor?.reduce_summary ?? false,
      consolidate_summary: flavor?.consolidate_summary ?? false,
      // Failover configuration
      failover_flavor_id: flavor?.failover_flavor_id || undefined,
      failover_enabled: flavor?.failover_enabled ?? false,
      failover_on_timeout: flavor?.failover_on_timeout ?? true,
      failover_on_rate_limit: flavor?.failover_on_rate_limit ?? true,
      failover_on_model_error: flavor?.failover_on_model_error ?? true,
      failover_on_content_filter: flavor?.failover_on_content_filter ?? false,
      max_failover_depth: flavor?.max_failover_depth ?? 3,
    },
  });

  const selectedModelId = form.watch('model_id');

  // Find selected model to display limits
  const selectedModel = models.find(m => m.id === selectedModelId);
  const selectedModelLimits = selectedModel ? getEffectiveModelLimits(selectedModel) : null;

  const processingMode = form.watch('processing_mode');

  // Prompt placeholder validation
  const [promptValidation, setPromptValidation] = useState<PromptValidationResult | null>(null);
  const userPromptContent = form.watch('prompt_user_content');

  // Validate prompt placeholders when content or mode changes
  useEffect(() => {
    if (userPromptContent && processingMode) {
      const result = validatePromptForMode(
        userPromptContent,
        processingMode as 'single_pass' | 'iterative'
      );
      setPromptValidation(result);
    } else {
      setPromptValidation(null);
    }
  }, [userPromptContent, processingMode]);

  // Helper functions for conditional rendering based on service type
  const shouldShowPrompt = (fieldName: string) => {
    if (!serviceTypeConfig) return true; // Show all if config not loaded
    return !!serviceTypeConfig.prompts[fieldName];
  };

  const isPromptRequired = (fieldName: string) => {
    if (!serviceTypeConfig) return false;
    return serviceTypeConfig.prompts[fieldName]?.required ?? false;
  };

  const getPromptDescription = (fieldName: string) => {
    if (!serviceTypeConfig) return '';
    const config = serviceTypeConfig.prompts[fieldName];
    if (!config) return '';
    return locale === 'fr' ? config.description_fr : config.description_en;
  };

  // Service type capabilities
  const supportsReduce = serviceTypeConfig?.supports_reduce ?? true;
  const supportsChunking = serviceTypeConfig?.supports_chunking ?? true;

  const onSubmit = async (data: FlavorFormData) => {
    try {
      // Convert "none" and null to undefined and prepare data for API
      // Helper to convert null/empty/none to undefined
      const toUndefined = <T,>(val: T | null | undefined | 'none'): T | undefined =>
        val === null || val === undefined || val === 'none' || val === '' ? undefined : val;

      const cleanedData = {
        ...data,
        // Keep inline content fields
        prompt_system_content: data.prompt_system_content || undefined,
        prompt_user_content: data.prompt_user_content || undefined,
        prompt_reduce_content: supportsReduce ? (data.prompt_reduce_content || undefined) : undefined,

        // Clean up "none" and null values for template IDs
        system_prompt_id: toUndefined(data.system_prompt_id),
        user_prompt_template_id: toUndefined(data.user_prompt_template_id),
        reduce_prompt_id: toUndefined(data.reduce_prompt_id),

        // Placeholder extraction configuration
        placeholder_extraction_prompt_id: toUndefined(data.placeholder_extraction_prompt_id),

        // Convert null to undefined for nullable numeric fields
        estimated_cost_per_1k_tokens: data.estimated_cost_per_1k_tokens ?? undefined,
        max_concurrent_requests: data.max_concurrent_requests ?? undefined,
        create_new_turn_after: data.create_new_turn_after ?? undefined,
        max_new_turns: data.max_new_turns ?? undefined,
        summary_turns: data.summary_turns ?? undefined,

        // Convert null to undefined for nullable string fields
        tokenizer_override: toUndefined(data.tokenizer_override),

        // Fallback configuration - convert null to undefined
        fallback_flavor_id: toUndefined(data.fallback_flavor_id),

        // Categorization configuration - convert null to undefined
        categorization_prompt_id: toUndefined(data.categorization_prompt_id),

        // Failover configuration
        failover_flavor_id: toUndefined(data.failover_flavor_id),
        failover_enabled: data.failover_enabled,
        failover_on_timeout: data.failover_on_timeout,
        failover_on_rate_limit: data.failover_on_rate_limit,
        failover_on_model_error: data.failover_on_model_error,
        failover_on_content_filter: data.failover_on_content_filter,
        max_failover_depth: data.max_failover_depth,
      };

      if (flavor) {
        // Update existing flavor
        await updateFlavorMutation.mutateAsync({
          serviceId: service.id,
          flavorId: flavor.id,
          data: cleanedData,
        });
      } else {
        // Add new flavor
        await addFlavorMutation.mutateAsync({
          serviceId: service.id,
          data: cleanedData,
        });
      }
      onSuccess();
    } catch (error: unknown) {
      // Error handled by mutation
      console.error('Flavor form error:', error);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Flavor Name */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.name')}</FormLabel>
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
              <FormLabel>{t('fields.modelId')}</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
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
        {selectedModelLimits && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <div className="flex flex-wrap gap-4 text-sm">
                <div>
                  <span className="font-medium">{tLimits('contextLength')}:</span>{' '}
                  {formatTokens(selectedModelLimits.contextLength)} tokens
                </div>
                <div>
                  <span className="font-medium">{tLimits('maxGeneration')}:</span>{' '}
                  {formatTokens(selectedModelLimits.maxGeneration)} tokens
                </div>
              </div>
            </AlertDescription>
          </Alert>
        )}

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

        {/* Priority */}
        <FormField
          control={form.control}
          name="priority"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.priority')}</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  min={0}
                  {...field}
                  value={field.value || 0}
                  onChange={(e) => field.onChange(parseInt(e.target.value) || 0)}
                />
              </FormControl>
              <FormDescription>{t('descriptions.priority')}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

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

        {/* Note: max_tokens is inherited from model.max_generation_length */}

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

        {/* Frequency Penalty Slider */}
        <FormField
          control={form.control}
          name="frequency_penalty"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('fields.frequencyPenalty')}: {field.value}</FormLabel>
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
              <FormLabel>{t('fields.presencePenalty')}: {field.value}</FormLabel>
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
                  onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                />
              </FormControl>
              <FormDescription>{t('descriptions.maxConcurrentRequests')}</FormDescription>
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

        {/* Processing Mode Section */}
        {(supportsReduce || supportsChunking) && (
          <div className="border-t pt-4 mt-4">
            <h3 className="text-sm font-medium mb-4">{t('processingMode.label')}</h3>

            {/* Preset Selector */}
            <div className="mb-4">
              <FlavorPresetSelector
                serviceType={service.service_type}
                onSelect={(config) => {
                  // Only apply applicable config based on service type capabilities
                  if (config.processing_mode && (
                    config.processing_mode !== 'iterative' || supportsChunking
                  )) {
                    form.setValue('processing_mode', config.processing_mode);
                  }
                  if (config.temperature !== undefined) form.setValue('temperature', config.temperature);
                  if (config.top_p !== undefined) form.setValue('top_p', config.top_p);
                  if (supportsChunking) {
                    if (config.max_new_turns !== undefined) form.setValue('max_new_turns', config.max_new_turns);
                    if (config.summary_turns !== undefined) form.setValue('summary_turns', config.summary_turns);
                    if (config.create_new_turn_after !== undefined) form.setValue('create_new_turn_after', config.create_new_turn_after);
                  }
                  if (supportsReduce && config.reduce_summary !== undefined) {
                    form.setValue('reduce_summary', config.reduce_summary);
                  }
                }}
              />
            </div>

            {/* Processing Mode Select - filter options by service type */}
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

            {/* Fallback Flavor selector (only for single_pass) */}
            {form.watch('processing_mode') === 'single_pass' && (
              <FormField
                control={form.control}
                name="fallback_flavor_id"
                render={({ field }) => (
                  <FormItem className="mt-4">
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
                        {allFlavors
                          .filter(f => f.id !== flavor?.id && f.is_active)
                          .map((f) => (
                            <SelectItem key={f.id} value={f.id}>
                              <span className="font-medium">{f.service_name}</span>
                              <span className="text-muted-foreground"> / {f.name}</span>
                              <Badge variant="outline" className="ml-2 text-xs">
                                {f.processing_mode}
                              </Badge>
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
          </div>
        )}

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

          {form.watch('failover_enabled') && (
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
                        {allFlavors
                          .filter(f => f.id !== flavor?.id && f.is_active)
                          .map((f) => (
                            <SelectItem key={f.id} value={f.id}>
                              <span className="font-medium">{f.service_name}</span>
                              <span className="text-muted-foreground"> / {f.name}</span>
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

        {/* System Prompt - Conditional with Required/Optional badges */}
        {shouldShowPrompt('system_prompt') && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label>{t('prompts.system')}</Label>
              <Badge variant={isPromptRequired('system_prompt') ? 'destructive' : 'outline'} className="text-xs">
                {isPromptRequired('system_prompt') ? tCommon('required') : tCommon('optional')}
              </Badge>
            </div>
            {getPromptDescription('system_prompt') && (
              <p className="text-sm text-muted-foreground">{getPromptDescription('system_prompt')}</p>
            )}
            <FlavorPromptEditor
              type="system"
              value={form.watch('prompt_system_content') || ''}
              onChange={(value) => form.setValue('prompt_system_content', value)}
              onLoadTemplate={() => {
                setActivePromptType('system');
                setTemplateBrowserOpen(true);
              }}
              onSaveTemplate={() => {
                setActivePromptType('system');
                setSaveTemplateDialogOpen(true);
              }}
            />
            {form.watch('system_prompt_id') && (
              <p className="text-xs text-muted-foreground">
                {t('loadedFromTemplate')}: {form.watch('system_prompt_id')}
              </p>
            )}
          </div>
        )}

        {/* User Prompt - Always shown with Required badge */}
        {shouldShowPrompt('user_prompt') && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label>{t('prompts.user')}</Label>
              <Badge variant="destructive" className="text-xs">
                {tCommon('required')}
              </Badge>
            </div>
            {getPromptDescription('user_prompt') && (
              <p className="text-sm text-muted-foreground">{getPromptDescription('user_prompt')}</p>
            )}
            <FlavorPromptEditor
              type="user"
              value={form.watch('prompt_user_content') || ''}
              onChange={(value) => form.setValue('prompt_user_content', value)}
              onLoadTemplate={() => {
                setActivePromptType('user');
                setTemplateBrowserOpen(true);
              }}
              onSaveTemplate={() => {
                setActivePromptType('user');
                setSaveTemplateDialogOpen(true);
              }}
            />
            {form.watch('user_prompt_template_id') && (
              <p className="text-xs text-muted-foreground">
                {t('loadedFromTemplate')}: {form.watch('user_prompt_template_id')}
              </p>
            )}
            {/* Prompt placeholder validation error */}
            {promptValidation && !promptValidation.valid && (
              <Alert variant="destructive" className="mt-2">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="font-medium">
                    {t('validation.promptPlaceholderMismatch')}
                  </div>
                  <div className="text-sm mt-1">
                    {processingMode === 'iterative'
                      ? t('validation.iterativeRequires2')
                      : t('validation.singleRequires1')
                    }
                  </div>
                  <div className="text-sm">
                    {t('validation.promptHasN', { count: promptValidation.placeholderCount })}
                  </div>
                  <div className="text-sm mt-1 text-muted-foreground">
                    {t('validation.selectDifferentPrompt')}
                  </div>
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {/* Reduce Prompt - Only for services that support reduce */}
        {supportsReduce && shouldShowPrompt('reduce_prompt') && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label>{t('prompts.reduce')}</Label>
              <Badge variant="outline" className="text-xs">
                {tCommon('optional')}
              </Badge>
            </div>
            {getPromptDescription('reduce_prompt') && (
              <p className="text-sm text-muted-foreground">{getPromptDescription('reduce_prompt')}</p>
            )}
            <FlavorPromptEditor
              type="reduce"
              value={form.watch('prompt_reduce_content') || ''}
              onChange={(value) => form.setValue('prompt_reduce_content', value)}
              onLoadTemplate={() => {
                setActivePromptType('reduce');
                setTemplateBrowserOpen(true);
              }}
              onSaveTemplate={() => {
                setActivePromptType('reduce');
                setSaveTemplateDialogOpen(true);
              }}
            />
            {form.watch('reduce_prompt_id') && (
              <p className="text-xs text-muted-foreground">
                {t('loadedFromTemplate')}: {form.watch('reduce_prompt_id')}
              </p>
            )}
          </div>
        )}

        {/* Advanced Configuration */}
        <Collapsible className="border rounded-lg p-4">
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="w-full justify-between p-0">
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

        {/* Placeholder Extraction Configuration */}
        <Collapsible className="border rounded-lg p-4">
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="w-full justify-between p-0">
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
                        .filter((p) => p.name.toLowerCase().includes('extract') || p.name.toLowerCase().includes('placeholder'))
                        .map((prompt) => (
                          <SelectItem key={prompt.id} value={prompt.id}>
                            {prompt.name}
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

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            {tCommon('cancel')}
          </Button>
          <Button
            type="submit"
            disabled={
              addFlavorMutation.isPending ||
              updateFlavorMutation.isPending ||
              (promptValidation !== null && !promptValidation.valid)
            }
          >
            {flavor ? tCommon('update') : tCommon('create')}
          </Button>
        </div>
      </form>

      {/* Template Browser Dialog */}
      <TemplateBrowserDialog
        open={templateBrowserOpen}
        onClose={() => setTemplateBrowserOpen(false)}
        onSelect={(template) => {
          // Load template content into editor
          if (activePromptType === 'system') {
            form.setValue('prompt_system_content', template.content);
            form.setValue('system_prompt_id', template.id);
          } else if (activePromptType === 'user') {
            form.setValue('prompt_user_content', template.content);
            form.setValue('user_prompt_template_id', template.id);
          } else if (activePromptType === 'reduce') {
            form.setValue('prompt_reduce_content', template.content);
            form.setValue('reduce_prompt_id', template.id);
          }
          setTemplateBrowserOpen(false);
        }}
        category={activePromptType === 'reduce' ? 'user' : activePromptType}
        serviceType={service.service_type}
      />

      {/* Save as Template Dialog */}
      <SaveTemplateDialog
        open={saveTemplateDialogOpen}
        onClose={() => setSaveTemplateDialogOpen(false)}
        onSave={async (name, description) => {
          // Save current content as template
          let content = '';
          let promptCategory: 'system' | 'user' = 'user';
          let promptType: string | undefined = undefined;

          if (activePromptType === 'system') {
            content = form.watch('prompt_system_content') || '';
            promptCategory = 'system';
            promptType = 'standard';
          } else if (activePromptType === 'user') {
            content = form.watch('prompt_user_content') || '';
            promptCategory = 'user';
            promptType = 'standard';
          } else if (activePromptType === 'reduce') {
            content = form.watch('prompt_reduce_content') || '';
            promptCategory = 'user';
            promptType = 'reduce';
          }

          await createPromptMutation.mutateAsync({
            name,
            content,
            description,
            service_type: service.service_type,
            prompt_category: promptCategory,
            prompt_type: promptType,
          });

          setSaveTemplateDialogOpen(false);
        }}
      />
    </Form>
  );
}
