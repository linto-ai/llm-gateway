'use client';

import { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Eye } from 'lucide-react';

import { usePrompts } from '@/hooks/use-prompts';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface PromptSelectorProps {
  serviceType: string;
  category: 'system' | 'user';
  promptType?: string;
  value: string | null;
  onChange: (promptId: string | null, content?: string) => void;
  required?: boolean;
  disabled?: boolean;
  // Filter prompts by processing mode (based on placeholder count)
  // - 'single_pass': only show prompts with 1 placeholder
  // - 'iterative': only show prompts with 2 placeholders
  // - undefined: show all prompts
  processingMode?: 'single_pass' | 'iterative';
}

export function PromptSelector({
  serviceType,
  category,
  promptType,
  value,
  onChange,
  required = false,
  disabled = false,
  processingMode,
}: PromptSelectorProps) {
  const t = useTranslations('services.promptSelector');
  const locale = useLocale();

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [previewName, setPreviewName] = useState('');

  // Fetch prompts filtered by service_type, category, and prompt_type
  const { data: promptsResponse, isLoading } = usePrompts({
    service_type: serviceType,
    prompt_category: category,
    prompt_type: promptType,
    page_size: 100,
  });

  // Filter prompts by placeholder count based on processing mode
  const allPrompts = promptsResponse?.items || [];
  const prompts = allPrompts.filter((p) => {
    if (!processingMode) return true; // No filter
    const requiredPlaceholders = processingMode === 'iterative' ? 2 : 1;
    return p.placeholder_count === requiredPlaceholders;
  });
  const selectedPrompt = prompts.find((p) => p.id === value);

  const handlePreview = (content: string, name: string) => {
    setPreviewContent(content);
    setPreviewName(name);
    setPreviewOpen(true);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Select
          value={value || 'none'}
          onValueChange={(v) => {
            const selected = prompts.find((p) => p.id === v);
            onChange(v === 'none' ? null : v, selected?.content);
          }}
          disabled={disabled || isLoading}
        >
          <SelectTrigger className="flex-1">
            <SelectValue placeholder={t('selectPrompt')} />
          </SelectTrigger>
          <SelectContent>
            {!required && <SelectItem value="none">{t('none')}</SelectItem>}
            {prompts.length === 0 ? (
              <div className="p-2 text-sm text-muted-foreground">{t('noPrompts')}</div>
            ) : (
              prompts.map((prompt) => (
                <SelectItem key={prompt.id} value={prompt.id}>
                  <div className="flex items-center gap-2">
                    <span>{prompt.name}</span>
                    {prompt.description && (
                      <span className="text-xs text-muted-foreground truncate max-w-[150px]">
                        {locale === 'fr' ? prompt.description.fr : prompt.description.en}
                      </span>
                    )}
                  </div>
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>

        {selectedPrompt && (
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={() => handlePreview(selectedPrompt.content, selectedPrompt.name)}
            title={t('preview')}
          >
            <Eye className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {t('preview')}: {previewName}
            </DialogTitle>
          </DialogHeader>
          <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-md font-mono">
            {previewContent}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  );
}
