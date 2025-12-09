'use client';

import { useState } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { AlertCircle } from 'lucide-react';

import { FlavorWizardBasics } from './FlavorWizardBasics';
import { FlavorWizardProcessing } from './FlavorWizardProcessing';
import { FlavorWizardPrompts } from './FlavorWizardPrompts';
import { FlavorWizardAdvanced } from './FlavorWizardAdvanced';

import { useAddFlavor, useUpdateFlavor } from '@/hooks/use-services';
import { useServiceTypeConfig } from '@/hooks/use-service-types';
import { flavorFormSchema, type FlavorFormData } from '@/schemas/forms';
import { validatePromptForMode } from '@/lib/prompt-validation';
import type { FlavorResponse, ServiceResponse, OutputType } from '@/types/service';

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

interface FlavorWizardProps {
  service: ServiceResponse;
  flavor?: FlavorResponse;
  onSuccess: () => void;
  onCancel: () => void;
}

const STEPS = ['basics', 'processing', 'prompts', 'advanced'] as const;
type StepKey = (typeof STEPS)[number];

// Define which form fields belong to each step for validation
const STEP_FIELDS: Record<StepKey, (keyof FlavorFormData)[]> = {
  basics: ['name', 'model_id', 'description', 'is_default', 'is_active'],
  processing: ['processing_mode', 'temperature', 'top_p'],
  prompts: ['prompt_system_content', 'prompt_user_content', 'prompt_reduce_content'],
  advanced: [
    'frequency_penalty',
    'presence_penalty',
    'stop_sequences',
    'custom_params',
    'estimated_cost_per_1k_tokens',
    'max_concurrent_requests',
    'priority',
    'output_type',
    'tokenizer_override',
    // Placeholder extraction fields
    'placeholder_extraction_prompt_id',
    // Failover fields
    'failover_flavor_id',
    'failover_enabled',
    'failover_on_timeout',
    'failover_on_rate_limit',
    'failover_on_model_error',
    'failover_on_content_filter',
    'max_failover_depth',
  ],
};

export function FlavorWizard({ service, flavor, onSuccess, onCancel }: FlavorWizardProps) {
  const t = useTranslations('services.wizard');
  const tCommon = useTranslations('common');

  const [currentStep, setCurrentStep] = useState(0);
  const { data: serviceTypeConfig } = useServiceTypeConfig(service?.service_type);

  const addFlavorMutation = useAddFlavor();
  const updateFlavorMutation = useUpdateFlavor();

  const methods = useForm<FlavorFormData>({
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
      processing_mode: (flavor?.processing_mode || serviceTypeConfig?.default_processing_mode || 'iterative') as 'single_pass' | 'iterative',
      tokenizer_override: flavor?.tokenizer_override || '',
      // Chunking parameters - default create_new_turn_after to 100 for new flavors
      create_new_turn_after: flavor?.create_new_turn_after ?? 100,
      max_new_turns: flavor?.max_new_turns ?? undefined,
      summary_turns: flavor?.summary_turns ?? undefined,
      reduce_summary: flavor?.reduce_summary ?? false,
      consolidate_summary: flavor?.consolidate_summary ?? false,
      // Placeholder extraction configuration
      placeholder_extraction_prompt_id: flavor?.placeholder_extraction_prompt_id || undefined,
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

  const progress = ((currentStep + 1) / STEPS.length) * 100;

  const canProceed = async () => {
    const stepFields = STEP_FIELDS[STEPS[currentStep]];
    // Only validate name and model_id as required for basics step
    if (currentStep === 0) {
      return await methods.trigger(['name', 'model_id']);
    }

    // On prompts step, also validate placeholder count
    if (currentStep === 2) {
      const userPrompt = methods.getValues('prompt_user_content');
      const mode = methods.getValues('processing_mode');

      if (userPrompt && mode) {
        const validation = validatePromptForMode(
          userPrompt,
          mode as 'single_pass' | 'iterative'
        );
        if (!validation.valid) {
          return false;
        }
      }
    }

    return await methods.trigger(stepFields);
  };

  const handleNext = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (await canProceed()) {
      setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
    }
  };

  const handleBack = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  const onSubmit = async (data: FlavorFormData) => {
    try {
      // Only summary service type supports reduce
      const supportsReduce = serviceTypeConfig?.supports_reduce ?? (service.service_type === 'summary');

      // Prepare data for API - ensure proper type conversion
      // Note: API uses system_prompt_content, user_prompt_content, reduce_prompt_content
      const supportsChunking = serviceTypeConfig?.supports_chunking ?? true;
      const cleanedData = {
        name: data.name,
        model_id: data.model_id,
        description: data.description || undefined,
        is_default: data.is_default,
        is_active: data.is_active,
        temperature: data.temperature,
        top_p: data.top_p,
        frequency_penalty: data.frequency_penalty,
        presence_penalty: data.presence_penalty,
        stop_sequences: data.stop_sequences,
        custom_params: data.custom_params,
        estimated_cost_per_1k_tokens: data.estimated_cost_per_1k_tokens ?? undefined,
        max_concurrent_requests: data.max_concurrent_requests ?? undefined,
        priority: data.priority,
        output_type: data.output_type,
        processing_mode: data.processing_mode,
        // Fallback configuration (triggers when context is exceeded)
        fallback_flavor_id: data.fallback_flavor_id === 'none' ? undefined : (data.fallback_flavor_id || undefined),
        tokenizer_override: data.tokenizer_override || undefined,
        // Chunking parameters (only if service supports chunking)
        create_new_turn_after: supportsChunking ? (data.create_new_turn_after ?? undefined) : undefined,
        max_new_turns: supportsChunking ? (data.max_new_turns ?? undefined) : undefined,
        summary_turns: supportsChunking ? (data.summary_turns ?? undefined) : undefined,
        reduce_summary: supportsReduce ? data.reduce_summary : false,
        consolidate_summary: data.consolidate_summary,
        // Prompt content fields (API expects prompt_system_content etc)
        prompt_system_content: data.prompt_system_content || undefined,
        prompt_user_content: data.prompt_user_content || undefined,
        prompt_reduce_content: supportsReduce ? (data.prompt_reduce_content || undefined) : undefined,
        // Template reference IDs (converted to undefined if 'none')
        system_prompt_template_id: data.system_prompt_id === 'none' ? undefined : (data.system_prompt_id || undefined),
        user_prompt_template_id: data.user_prompt_template_id === 'none' ? undefined : (data.user_prompt_template_id || undefined),
        reduce_prompt_template_id: data.reduce_prompt_id === 'none' ? undefined : (data.reduce_prompt_id || undefined),
        // Placeholder extraction configuration
        placeholder_extraction_prompt_id: data.placeholder_extraction_prompt_id === 'none' ? undefined : (data.placeholder_extraction_prompt_id || undefined),
        // Failover configuration
        failover_flavor_id: data.failover_flavor_id === 'none' ? undefined : (data.failover_flavor_id || undefined),
        failover_enabled: data.failover_enabled,
        failover_on_timeout: data.failover_on_timeout,
        failover_on_rate_limit: data.failover_on_rate_limit,
        failover_on_model_error: data.failover_on_model_error,
        failover_on_content_filter: data.failover_on_content_filter,
        max_failover_depth: data.max_failover_depth,
      };

      if (flavor) {
        await updateFlavorMutation.mutateAsync({
          serviceId: service.id,
          flavorId: flavor.id,
          data: cleanedData,
        });
      } else {
        await addFlavorMutation.mutateAsync({
          serviceId: service.id,
          data: cleanedData,
        });
      }
      onSuccess();
    } catch {
      // Error handled by mutation
    }
  };

  const isSubmitting = addFlavorMutation.isPending || updateFlavorMutation.isPending;
  const { isDirty } = methods.formState;

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={methods.handleSubmit(onSubmit)}
        onKeyDown={(e) => {
          // Prevent Enter key from submitting the form unless on the final step
          // BUT allow Enter in textareas for newlines
          const isTextarea = (e.target as HTMLElement).tagName === 'TEXTAREA';
          if (e.key === 'Enter' && currentStep < STEPS.length - 1 && !isTextarea) {
            e.preventDefault();
          }
        }}
        className="space-y-6"
      >
        {/* Progress indicator */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <Progress value={progress} className="h-2 flex-1" />
            {flavor && isDirty && (
              <Badge variant="outline" className="ml-4 text-yellow-600 border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
                <AlertCircle className="h-3 w-3 mr-1" />
                {t('unsavedChanges')}
              </Badge>
            )}
          </div>
          <div className="flex justify-between mt-3 text-sm text-muted-foreground">
            {STEPS.map((step, i) => (
              <button
                key={step}
                type="button"
                onClick={() => i < currentStep && setCurrentStep(i)}
                className={`transition-colors ${
                  i === currentStep
                    ? 'font-medium text-foreground'
                    : i < currentStep
                      ? 'cursor-pointer hover:text-foreground'
                      : 'cursor-default'
                }`}
                disabled={i > currentStep}
              >
                {t(`steps.${step}`)}
              </button>
            ))}
          </div>
        </div>

        {/* Step content */}
        <Card>
          <CardContent className="pt-6">
            {currentStep === 0 && <FlavorWizardBasics />}
            {currentStep === 1 && (
              <FlavorWizardProcessing
                service={service}
                config={serviceTypeConfig ?? undefined}
                currentFlavorId={flavor?.id}
              />
            )}
            {currentStep === 2 && (
              <FlavorWizardPrompts service={service} config={serviceTypeConfig ?? undefined} />
            )}
            {currentStep === 3 && (
              <FlavorWizardAdvanced service={service} config={serviceTypeConfig ?? undefined} flavor={flavor} />
            )}
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="flex justify-between">
          <div className="flex gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={onCancel}
            >
              {tCommon('cancel')}
            </Button>
            {currentStep > 0 && (
              <Button
                type="button"
                variant="outline"
                onClick={handleBack}
              >
                {t('previous')}
              </Button>
            )}
          </div>

          {currentStep < STEPS.length - 1 ? (
            <Button type="button" onClick={handleNext}>
              {t('next')}
            </Button>
          ) : (
            <Button type="submit" disabled={isSubmitting}>
              {flavor ? tCommon('update') : t('finish')}
            </Button>
          )}
        </div>
      </form>
    </FormProvider>
  );
}
