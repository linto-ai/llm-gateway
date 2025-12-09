'use client';

import { useTranslations } from 'next-intl';
import { Info, ExternalLink } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';

import type { ModelResponse } from '@/types/model';

interface ModelLimitsSectionProps {
  model: ModelResponse;
  onChange: (field: string, value: number) => void;
}

export function ModelLimitsSection({
  model,
  onChange,
}: ModelLimitsSectionProps) {
  const t = useTranslations('models.limits');

  // Format token count for display
  const formatTokens = (count: number) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return count.toLocaleString();
    return count.toString();
  };

  const availableForInput = model.context_length - model.max_generation_length;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('title')}</CardTitle>
        <CardDescription>{t('subtitle')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Educational Content (Collapsible) */}
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 p-0 h-auto">
              <Info className="h-4 w-4" />
              <span className="text-sm underline">{t('info.title')}</span>
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-4">
            <Alert>
              <AlertDescription className="space-y-3 text-sm">
                <p><strong>{t('info.contextWindow')}</strong></p>
                <p>{t('info.contextWindowDesc')}</p>
                <p className="text-muted-foreground">{t('info.contextWindowExample')}</p>

                <p><strong>{t('info.maxGeneration')}</strong></p>
                <p>{t('info.maxGenerationDesc')}</p>
                <p className="text-muted-foreground">{t('info.maxGenerationExample')}</p>

                <p className="font-medium text-primary">{t('info.formula')}</p>
                <p className="text-muted-foreground">{t('info.formulaExample')}</p>
              </AlertDescription>
            </Alert>
          </CollapsibleContent>
        </Collapsible>

        {/* Available for Input Display */}
        <div className="p-4 bg-muted rounded-lg">
          <p className="text-xs text-muted-foreground">{t('availableForInput')}</p>
          <p className="font-mono text-lg">{formatTokens(availableForInput)} tokens</p>
        </div>

        {/* Edit Inputs - directly edit base values */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="context_length">{t('contextLength')}</Label>
            <Input
              id="context_length"
              type="number"
              value={model.context_length}
              onChange={(e) => onChange('context_length', parseInt(e.target.value, 10) || 0)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="max_generation_length">{t('maxGeneration')}</Label>
            <Input
              id="max_generation_length"
              type="number"
              value={model.max_generation_length}
              onChange={(e) => onChange('max_generation_length', parseInt(e.target.value, 10) || 0)}
            />
          </div>
        </div>

        {/* External resource link */}
        <p className="text-xs text-muted-foreground">
          {t('resource')}{' '}
          <a
            href="https://github.com/taylorwilsdon/llm-context-limits"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-primary hover:underline"
          >
            llm-context-limits
            <ExternalLink className="h-3 w-3" />
          </a>
        </p>
      </CardContent>
    </Card>
  );
}
