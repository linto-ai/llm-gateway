'use client';

import { useTranslations } from 'next-intl';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

interface FlavorPromptEditorProps {
  type: 'system' | 'user' | 'reduce';
  value: string;
  onChange: (value: string) => void;
  onLoadTemplate: () => void;
  onSaveTemplate: () => void;
  disabled?: boolean;
  error?: string;
}

export function FlavorPromptEditor({
  type,
  value,
  onChange,
  onLoadTemplate,
  onSaveTemplate,
  disabled = false,
  error,
}: FlavorPromptEditorProps) {
  const t = useTranslations('services.flavors.prompts');

  const charCount = value?.length || 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor={`prompt-${type}`}>{t(type)}</Label>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onLoadTemplate}
            disabled={disabled}
          >
            {t('loadTemplate')}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onSaveTemplate}
            disabled={disabled || !value}
          >
            {t('saveAsTemplate')}
          </Button>
        </div>
      </div>
      <Textarea
        id={`prompt-${type}`}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t(`${type}Placeholder`)}
        disabled={disabled}
        rows={10}
        className="font-mono text-sm"
      />
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>{t('characters', { count: charCount })}</span>
        {error && <span className="text-destructive">{error}</span>}
      </div>
    </div>
  );
}
