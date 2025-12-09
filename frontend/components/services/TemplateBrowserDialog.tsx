'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { usePromptTemplates } from '@/hooks/use-prompts';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTranslations } from 'next-intl';
import type { PromptResponse, PromptCategory } from '@/types/prompt';

interface TemplateBrowserDialogProps {
  open: boolean;
  onClose: () => void;
  onSelect: (template: PromptResponse) => void;
  category: PromptCategory | 'system' | 'user';
  serviceType?: string;
}

export function TemplateBrowserDialog({
  open,
  onClose,
  onSelect,
  category,
  serviceType,
}: TemplateBrowserDialogProps) {
  const t = useTranslations('services.flavors');

  const { data: templatesResponse } = usePromptTemplates({
    category: category as PromptCategory,
    service_type: serviceType,
  });

  const templates = templatesResponse?.items || [];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('selectTemplate')}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-96">
          <div className="space-y-2">
            {templates.map((template) => (
              <div
                key={template.id}
                className="border rounded-lg p-4 hover:bg-accent cursor-pointer"
                onClick={() => onSelect(template)}
              >
                <h3 className="font-medium">{template.name}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {template.description?.en || template.description?.fr}
                </p>
                <pre className="text-xs mt-2 bg-muted p-2 rounded overflow-x-auto">
                  {template.content.substring(0, 150)}...
                </pre>
              </div>
            ))}
            {templates.length === 0 && (
              <p className="text-center text-muted-foreground py-8">
                {t('noTemplates')}
              </p>
            )}
          </div>
        </ScrollArea>
        <div className="flex justify-end">
          <Button type="button" variant="outline" onClick={onClose}>
            {t('cancel')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
