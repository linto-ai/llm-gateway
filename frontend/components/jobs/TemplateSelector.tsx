'use client';

import { useTranslations, useLocale } from 'next-intl';
import { FileText } from 'lucide-react';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Label } from '@/components/ui/label';

import { useDocumentTemplates } from '@/hooks/use-document-templates';
import { getLocalizedName, getScopeBadgeVariant } from '@/lib/template-utils';
import type { TemplateScope } from '@/types/document-template';

interface TemplateSelectorProps {
  value?: string;
  onChange: (templateId: string | undefined) => void;
  organizationId?: string;
  label?: boolean;
  placeholder?: string;
}

/**
 * Dropdown to select a template for export.
 * Fetches templates with hierarchical visibility (system + org templates).
 */
export function TemplateSelector({
  value,
  onChange,
  organizationId,
  label = true,
  placeholder,
}: TemplateSelectorProps) {
  const t = useTranslations('jobs.export');
  const tTemplates = useTranslations('templates');
  const locale = useLocale();

  // Fetch templates visible to the current context
  const { data: templates = [], isLoading } = useDocumentTemplates({
    organization_id: organizationId,
    include_system: true,
  });

  // Get scope label
  const getScopeLabel = (scope: TemplateScope): string => {
    return tTemplates(`scope.${scope}`);
  };

  // Handle selection change
  const handleChange = (newValue: string) => {
    // "default" means no specific template selected
    onChange(newValue === 'default' ? undefined : newValue);
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {label && <Skeleton className="h-4 w-24" />}
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {label && (
        <Label className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          {t('selectTemplate')}
        </Label>
      )}
      <Select
        value={value || 'default'}
        onValueChange={handleChange}
      >
        <SelectTrigger>
          <SelectValue placeholder={placeholder || t('selectTemplate')} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="default">
            <div className="flex items-center gap-2">
              <span>{t('defaultTemplate')}</span>
            </div>
          </SelectItem>
          {templates.map((template) => (
            <SelectItem key={template.id} value={template.id}>
              <div className="flex items-center gap-2">
                <span>{getLocalizedName(template, locale)}</span>
                <Badge
                  variant={getScopeBadgeVariant(template.scope)}
                  className="text-xs"
                >
                  {getScopeLabel(template.scope)}
                </Badge>
                {template.is_default && (
                  <Badge variant="outline" className="text-xs">
                    {tTemplates('isDefault')}
                  </Badge>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
