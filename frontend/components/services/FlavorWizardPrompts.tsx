'use client';

import { useState, useEffect, useMemo } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslations, useLocale } from 'next-intl';

import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { AlertCircle, Eye, Save } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { SaveTemplateDialog } from './SaveTemplateDialog';
import { usePrompts, useCreatePrompt } from '@/hooks/use-prompts';
import { validatePromptForMode, type PromptValidationResult } from '@/lib/prompt-validation';
import type { FlavorFormData } from '@/schemas/forms';
import type { ServiceResponse } from '@/types/service';
import type { ServiceTypeConfig } from '@/types/service-type';

interface FlavorWizardPromptsProps {
  service: ServiceResponse;
  config?: ServiceTypeConfig;
}

export function FlavorWizardPrompts({ service, config }: FlavorWizardPromptsProps) {
  const t = useTranslations('services.flavors');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const form = useFormContext<FlavorFormData>();

  // State for dialogs
  const [saveTemplateDialogOpen, setSaveTemplateDialogOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [previewName, setPreviewName] = useState('');
  const [activePromptType, setActivePromptType] = useState<'system' | 'user' | 'reduce'>('system');

  // Watch form values
  const userPromptContent = form.watch('prompt_user_content');
  const processingMode = form.watch('processing_mode');
  const reduceSummary = form.watch('reduce_summary');

  // Prompt placeholder validation
  const [promptValidation, setPromptValidation] = useState<PromptValidationResult | null>(null);

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

  const createPromptMutation = useCreatePrompt();

  // Determine expected placeholder count for the current mode
  const expectedPlaceholders = processingMode === 'iterative' ? 2 : 1;

  // Fetch prompts with new filtering logic based on prompt_category and prompt_type
  // System prompts: prompt_category=system + service_type
  const { data: systemPromptsResponse } = usePrompts({
    service_type: service.service_type,
    prompt_category: 'system',
    page_size: 100,
  });

  // User prompts: prompt_category=user + service_type (filter client-side for standard type or null)
  const { data: userPromptsResponse } = usePrompts({
    service_type: service.service_type,
    prompt_category: 'user',
    page_size: 100,
  });

  // Reduce prompts: prompt_type=reduce + service_type
  const { data: reducePromptsResponse } = usePrompts({
    service_type: service.service_type,
    prompt_type: 'reduce',
    page_size: 100,
  });

  // Filter user prompts to exclude reduce type (standard or null only)
  const mainUserPrompts = useMemo(() => {
    const prompts = userPromptsResponse?.items || [];
    return prompts.filter(p =>
      !p.prompt_type || p.prompt_type.code === 'standard'
    );
  }, [userPromptsResponse]);

  // Filter user prompts by placeholder count based on processing mode
  // Uses placeholder_count from API (computed field)
  const filteredUserPrompts = useMemo(() => {
    return mainUserPrompts.filter((p) => p.placeholder_count === expectedPlaceholders);
  }, [mainUserPrompts, expectedPlaceholders]);

  // Also keep incompatible prompts to show them greyed out
  const incompatibleUserPrompts = useMemo(() => {
    return mainUserPrompts.filter((p) => p.placeholder_count !== expectedPlaceholders);
  }, [mainUserPrompts, expectedPlaceholders]);

  const systemPrompts = systemPromptsResponse?.items || [];
  const reducePrompts = reducePromptsResponse?.items || [];

  // Auto-populate prompt content when a prompt ID is selected but content is empty
  // This handles the case of editing a flavor that has prompt IDs but empty content fields
  useEffect(() => {
    const systemPromptId = form.getValues('system_prompt_id');
    const systemContent = form.getValues('prompt_system_content');
    if (systemPromptId && !systemContent && systemPrompts.length > 0) {
      const prompt = systemPrompts.find(p => p.id === systemPromptId);
      if (prompt?.content) {
        form.setValue('prompt_system_content', prompt.content);
      }
    }
  }, [systemPrompts, form]);

  useEffect(() => {
    const userPromptId = form.getValues('user_prompt_template_id');
    const userContent = form.getValues('prompt_user_content');
    if (userPromptId && !userContent && mainUserPrompts.length > 0) {
      const prompt = mainUserPrompts.find(p => p.id === userPromptId);
      if (prompt?.content) {
        form.setValue('prompt_user_content', prompt.content);
      }
    }
  }, [mainUserPrompts, form]);

  useEffect(() => {
    const reducePromptId = form.getValues('reduce_prompt_id');
    const reduceContent = form.getValues('prompt_reduce_content');
    if (reducePromptId && !reduceContent && reducePrompts.length > 0) {
      const prompt = reducePrompts.find(p => p.id === reducePromptId);
      if (prompt?.content) {
        form.setValue('prompt_reduce_content', prompt.content);
      }
    }
  }, [reducePrompts, form]);

  // Only summary service type supports reduce; derive from config or service type
  const supportsReduce = config?.supports_reduce ?? (service.service_type === 'summary');
  // Only show reduce prompt if reduce is supported AND reduce_summary is enabled
  const showReducePrompt = supportsReduce && reduceSummary;

  // Helper functions for conditional rendering
  const shouldShowPrompt = (fieldName: string) => {
    // If no config or prompts config is empty, show all prompts by default
    if (!config || !config.prompts || Object.keys(config.prompts).length === 0) return true;
    return !!config.prompts[fieldName];
  };

  const isPromptRequired = (fieldName: string) => {
    if (!config) return false;
    return config.prompts[fieldName]?.required ?? false;
  };

  const getPromptDescription = (fieldName: string) => {
    if (!config) return '';
    const promptConfig = config.prompts[fieldName];
    if (!promptConfig) return '';
    return locale === 'fr' ? promptConfig.description_fr : promptConfig.description_en;
  };

  // Handler when a prompt is selected
  const handlePromptSelect = (
    type: 'system' | 'user' | 'reduce',
    promptId: string | null,
    prompts: Array<{ id: string; content: string }>
  ) => {
    const selected = prompts.find((p) => p.id === promptId);
    const content = selected?.content;

    if (type === 'system') {
      form.setValue('system_prompt_id', promptId || undefined);
      if (content) form.setValue('prompt_system_content', content);
    } else if (type === 'user') {
      form.setValue('user_prompt_template_id', promptId || undefined);
      if (content) form.setValue('prompt_user_content', content);
    } else if (type === 'reduce') {
      form.setValue('reduce_prompt_id', promptId || undefined);
      if (content) form.setValue('prompt_reduce_content', content);
    }
  };

  const handlePreview = (content: string, name: string) => {
    setPreviewContent(content);
    setPreviewName(name);
    setPreviewOpen(true);
  };

  // Render a unified prompt section
  const renderPromptSection = (
    type: 'system' | 'user' | 'reduce',
    label: string,
    required: boolean,
    description: string | undefined,
    prompts: Array<{ id: string; name: string; content: string; placeholder_count: number }>,
    selectedId: string | null | undefined,
    content: string,
    incompatiblePrompts?: Array<{ id: string; name: string; content: string; placeholder_count: number }>
  ) => {
    const charCount = content?.length || 0;

    return (
      <div className="space-y-4 border rounded-lg p-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Label className="text-base font-medium">{label}</Label>
            <Badge
              variant={required ? 'destructive' : 'outline'}
              className="text-xs"
            >
              {required ? tCommon('required') : tCommon('optional')}
            </Badge>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setActivePromptType(type);
              setSaveTemplateDialogOpen(true);
            }}
            disabled={!content}
            title={t('prompts.saveAsTemplate')}
          >
            <Save className="h-4 w-4" />
          </Button>
        </div>

        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}

        {/* Quick select dropdown */}
        <div className="flex items-center gap-2">
          <Select
            value={selectedId || 'none'}
            onValueChange={(v) => handlePromptSelect(type, v === 'none' ? null : v, [...prompts, ...(incompatiblePrompts || [])])}
          >
            <SelectTrigger className="flex-1">
              <SelectValue placeholder={t('promptSelector.selectPrompt')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t('promptSelector.none')}</SelectItem>
              {prompts.length === 0 && (!incompatiblePrompts || incompatiblePrompts.length === 0) ? (
                <div className="p-2 text-sm text-muted-foreground">{t('promptSelector.noPrompts')}</div>
              ) : (
                <>
                  {prompts.map((prompt) => (
                    <SelectItem key={prompt.id} value={prompt.id}>
                      <span>{prompt.name}</span>
                    </SelectItem>
                  ))}
                  {incompatiblePrompts && incompatiblePrompts.length > 0 && (
                    <>
                      <div className="px-2 py-1 text-xs text-muted-foreground border-t mt-1 pt-1">
                        {t('promptSelector.incompatible', { count: expectedPlaceholders })}
                      </div>
                      {incompatiblePrompts.map((prompt) => (
                        <SelectItem
                          key={prompt.id}
                          value={prompt.id}
                          className="opacity-50"
                        >
                          <div className="flex items-center gap-2">
                            <span className="line-through">{prompt.name}</span>
                            <span className="text-xs text-muted-foreground">
                              ({prompt.placeholder_count} {'{}'})
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </>
                  )}
                </>
              )}
            </SelectContent>
          </Select>

          {selectedId && prompts.find((p) => p.id === selectedId) && (
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={() => {
                const selected = prompts.find((p) => p.id === selectedId);
                if (selected) handlePreview(selected.content, selected.name);
              }}
              title={t('promptSelector.preview')}
            >
              <Eye className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Text editor */}
        <div className="space-y-2">
          <Textarea
            value={content || ''}
            onChange={(e) => {
              if (type === 'system') form.setValue('prompt_system_content', e.target.value);
              else if (type === 'user') form.setValue('prompt_user_content', e.target.value);
              else if (type === 'reduce') form.setValue('prompt_reduce_content', e.target.value);
            }}
            placeholder={t(`prompts.${type}Placeholder`)}
            rows={8}
            className="font-mono text-sm"
          />
          <div className="text-xs text-muted-foreground text-right">
            {t('prompts.characters', { count: charCount })}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* System Prompt */}
      {shouldShowPrompt('system_prompt') && renderPromptSection(
        'system',
        t('prompts.system'),
        isPromptRequired('system_prompt'),
        getPromptDescription('system_prompt'),
        systemPrompts,
        form.watch('system_prompt_id'),
        form.watch('prompt_system_content') || ''
      )}

      {/* User Prompt */}
      {shouldShowPrompt('user_prompt') && (
        <>
          {renderPromptSection(
            'user',
            t('prompts.user'),
            true,
            getPromptDescription('user_prompt'),
            filteredUserPrompts,
            form.watch('user_prompt_template_id'),
            form.watch('prompt_user_content') || '',
            incompatibleUserPrompts
          )}

          {/* Validation error */}
          {promptValidation && !promptValidation.valid && (
            <Alert variant="destructive">
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
              </AlertDescription>
            </Alert>
          )}
        </>
      )}

      {/* Reduce Prompt - Only shown when reduce is enabled */}
      {showReducePrompt && shouldShowPrompt('reduce_prompt') && renderPromptSection(
        'reduce',
        t('prompts.reduce'),
        false,
        getPromptDescription('reduce_prompt'),
        reducePrompts,
        form.watch('reduce_prompt_id'),
        form.watch('prompt_reduce_content') || ''
      )}

      {/* Hint if reduce prompt is hidden */}
      {supportsReduce && !showReducePrompt && shouldShowPrompt('reduce_prompt') && (
        <p className="text-sm text-muted-foreground italic">
          {t('prompts.reduceHiddenHint')}
        </p>
      )}

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {t('promptSelector.preview')}: {previewName}
            </DialogTitle>
          </DialogHeader>
          <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-md font-mono">
            {previewContent}
          </pre>
        </DialogContent>
      </Dialog>

      {/* Save as Template Dialog */}
      <SaveTemplateDialog
        open={saveTemplateDialogOpen}
        onClose={() => setSaveTemplateDialogOpen(false)}
        onSave={async (name, description) => {
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
    </div>
  );
}
