'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { X, Plus } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';

interface FlavorConfigAdvancedProps {
  stopSequences: string[];
  customParams: Record<string, any>;
  onStopSequencesChange: (sequences: string[]) => void;
  onCustomParamsChange: (params: Record<string, any>) => void;
}

export function FlavorConfigAdvanced({
  stopSequences,
  customParams,
  onStopSequencesChange,
  onCustomParamsChange,
}: FlavorConfigAdvancedProps) {
  const t = useTranslations('flavors');
  const [customParamsJson, setCustomParamsJson] = useState(
    JSON.stringify(customParams, null, 2)
  );
  const [jsonError, setJsonError] = useState<string | null>(null);

  const addStopSequence = () => {
    if (stopSequences.length < 4) {
      onStopSequencesChange([...stopSequences, '']);
    }
  };

  const updateStopSequence = (index: number, value: string) => {
    const updated = [...stopSequences];
    updated[index] = value;
    onStopSequencesChange(updated);
  };

  const removeStopSequence = (index: number) => {
    const updated = stopSequences.filter((_, i) => i !== index);
    onStopSequencesChange(updated);
  };

  const handleCustomParamsChange = (value: string) => {
    setCustomParamsJson(value);
    try {
      const parsed = JSON.parse(value);
      onCustomParamsChange(parsed);
      setJsonError(null);
    } catch (error) {
      setJsonError(t('fields.customParamsError'));
    }
  };

  return (
    <div className="space-y-6">
      {/* Stop Sequences */}
      <div>
        <Label>{t('fields.stopSequences')}</Label>
        <p className="text-sm text-muted-foreground mb-2">
          {t('fields.stopSequencesDescription')}
        </p>
        <div className="space-y-2">
          {stopSequences.map((seq, idx) => (
            <div key={idx} className="flex gap-2">
              <Input
                value={seq}
                onChange={(e) => updateStopSequence(idx, e.target.value)}
                placeholder={t('fields.stopSequencePlaceholder')}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeStopSequence(idx)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          {stopSequences.length < 4 && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addStopSequence}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              {t('actions.addStopSequence')}
            </Button>
          )}
        </div>
      </div>

      {/* Custom Params JSON Editor */}
      <div>
        <Label>{t('fields.customParams')}</Label>
        <p className="text-sm text-muted-foreground mb-2">
          {t('fields.customParamsDescription')}
        </p>
        <Textarea
          value={customParamsJson}
          onChange={(e) => handleCustomParamsChange(e.target.value)}
          placeholder='{"key": "value"}'
          rows={8}
          className="font-mono text-sm"
        />
        {jsonError && (
          <p className="text-sm text-destructive mt-1">{jsonError}</p>
        )}
      </div>
    </div>
  );
}
