'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { FileText, Loader2 } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useSyntheticTemplates } from '@/hooks/use-synthetic-templates';
import { apiClient } from '@/lib/api-client';

interface SyntheticTemplateBrowserProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (filename: string, content: string) => void;
}

export function SyntheticTemplateBrowser({
  open,
  onOpenChange,
  onSelect,
}: SyntheticTemplateBrowserProps) {
  const t = useTranslations();
  const [languageFilter, setLanguageFilter] = useState<string>('all');
  const [errorTypeFilter, setErrorTypeFilter] = useState<string>('all');
  const [loadingTemplate, setLoadingTemplate] = useState<string | null>(null);

  const { data, isLoading } = useSyntheticTemplates();
  const templates = data?.templates || [];

  const filteredTemplates = templates.filter((template) => {
    if (languageFilter !== 'all' && template.language !== languageFilter) return false;
    if (errorTypeFilter !== 'all' && template.error_type !== errorTypeFilter) return false;
    return true;
  });

  const handleSelectTemplate = async (filename: string) => {
    setLoadingTemplate(filename);
    try {
      const response = await apiClient.syntheticTemplates.getContent(filename);
      onSelect(filename, response.content);
      onOpenChange(false);
    } catch {
      // Template loading failed - handled by UI state
    } finally {
      setLoadingTemplate(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    const kb = bytes / 1024;
    return `${kb.toFixed(1)} KB`;
  };

  const getErrorTypeBadgeKey = (errorType: string): string => {
    switch (errorType) {
      case 'perfect':
        return 'perfect';
      case 'diarization_errors':
        return 'diarization';
      case 'full_errors':
        return 'full';
      default:
        return errorType;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>{t('services.syntheticTemplates.title')}</DialogTitle>
          <DialogDescription>
            {t('services.syntheticTemplates.description')}
          </DialogDescription>
        </DialogHeader>

        {/* Filters */}
        <div className="flex gap-4 mb-4">
          <div className="flex-1">
            <Select value={languageFilter} onValueChange={setLanguageFilter}>
              <SelectTrigger>
                <SelectValue placeholder={t('services.syntheticTemplates.filterLanguage')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all')}</SelectItem>
                <SelectItem value="en">{t('services.syntheticTemplates.languages.en')}</SelectItem>
                <SelectItem value="fr">{t('services.syntheticTemplates.languages.fr')}</SelectItem>
                <SelectItem value="mixed">{t('services.syntheticTemplates.languages.mixed')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex-1">
            <Select value={errorTypeFilter} onValueChange={setErrorTypeFilter}>
              <SelectTrigger>
                <SelectValue placeholder={t('services.syntheticTemplates.filterErrorType')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all')}</SelectItem>
                <SelectItem value="perfect">{t('services.syntheticTemplates.errorTypes.perfect')}</SelectItem>
                <SelectItem value="diarization_errors">{t('services.syntheticTemplates.errorTypes.diarization')}</SelectItem>
                <SelectItem value="full_errors">{t('services.syntheticTemplates.errorTypes.full')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Template List */}
        <ScrollArea className="h-[400px] pr-4">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : filteredTemplates.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              {t('services.syntheticTemplates.noTemplates')}
            </p>
          ) : (
            <div className="space-y-2">
              {filteredTemplates.map((template) => (
                <div
                  key={template.filename}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                  onClick={() => handleSelectTemplate(template.filename)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleSelectTemplate(template.filename);
                    }
                  }}
                >
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{template.filename}</p>
                      <p className="text-sm text-muted-foreground">{template.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{template.language.toUpperCase()}</Badge>
                    <Badge variant={template.error_type === 'perfect' ? 'default' : 'secondary'}>
                      {t(`services.syntheticTemplates.errorTypes.${getErrorTypeBadgeKey(template.error_type)}`)}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatFileSize(template.size_bytes)}
                    </span>
                    {loadingTemplate === template.filename && (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
