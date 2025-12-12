'use client';

import { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { toast } from 'sonner';
import { Library, FileText, Download, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import {
  useGlobalDocumentTemplates,
  useImportDocumentTemplate,
} from '@/hooks/use-document-templates';
import {
  getLocalizedName,
  getLocalizedDescription,
  formatFileSize,
} from '@/lib/template-utils';
import { getPlaceholderName } from '@/types/document-template';
import type { DocumentTemplate } from '@/types/document-template';

interface TemplateLibraryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serviceId?: string;
  /** Called after successful import (copy) of a template */
  onImportSuccess?: () => void;
  /** Called when a template is selected (without importing). If provided, switches to selection mode. */
  onSelect?: (template: DocumentTemplate) => void;
}

/**
 * Dialog for browsing and importing global templates to a service.
 */
export function TemplateLibraryDialog({
  open,
  onOpenChange,
  serviceId,
  onImportSuccess,
  onSelect,
}: TemplateLibraryDialogProps) {
  const t = useTranslations('templates');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  const [processingId, setProcessingId] = useState<string | null>(null);

  const { data: globalTemplates = [], isLoading } = useGlobalDocumentTemplates();
  const importMutation = useImportDocumentTemplate();

  // Selection mode: just call onSelect and close
  const isSelectionMode = !!onSelect;

  // Handle template action (import or select depending on mode)
  const handleTemplateAction = async (template: DocumentTemplate) => {
    if (isSelectionMode) {
      // Selection mode: just call onSelect
      onSelect(template);
      onOpenChange(false);
      return;
    }

    // Import mode: copy template to service
    if (!serviceId) return;

    setProcessingId(template.id);
    try {
      await importMutation.mutateAsync({
        templateId: template.id,
        serviceId,
      });
      toast.success(t('library.importSuccess'));
      onImportSuccess?.();
    } catch (error: any) {
      // Handle various error formats
      const errorMessage = typeof error?.message === 'string'
        ? error.message
        : typeof error?.detail === 'string'
        ? error.detail
        : t('library.importError');
      toast.error(errorMessage);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Library className="h-5 w-5" />
            {t('library.title')}
          </DialogTitle>
          <DialogDescription>{t('library.subtitle')}</DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="flex justify-center items-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : globalTemplates.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium">{t('library.empty')}</p>
              <p className="text-sm text-muted-foreground">
                {t('library.emptyDescription')}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('table.name')}</TableHead>
                  <TableHead>{t('table.size')}</TableHead>
                  <TableHead>{t('table.placeholders')}</TableHead>
                  <TableHead>{t('table.createdAt')}</TableHead>
                  <TableHead className="text-right">{t('table.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {globalTemplates.map((template) => (
                  <TableRow key={template.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-blue-500" />
                        <div>
                          <div className="font-medium">{getLocalizedName(template, locale)}</div>
                          {getLocalizedDescription(template, locale) && (
                            <p className="text-sm text-muted-foreground">
                              {getLocalizedDescription(template, locale)}
                            </p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatFileSize(template.file_size)}
                    </TableCell>
                    <TableCell>
                      {template.placeholders && template.placeholders.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {template.placeholders.slice(0, 3).map((placeholder) => (
                            <Badge
                              key={placeholder}
                              variant="outline"
                              className="text-xs font-mono"
                            >
                              {`{{${getPlaceholderName(placeholder)}}}`}
                            </Badge>
                          ))}
                          {template.placeholders.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{template.placeholders.length - 3}
                            </Badge>
                          )}
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">
                          {t('noPlaceholders')}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDistanceToNow(new Date(template.created_at), {
                        addSuffix: true,
                      })}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        onClick={() => handleTemplateAction(template)}
                        disabled={processingId === template.id}
                      >
                        {processingId === template.id ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            {isSelectionMode ? tCommon('loading') : t('library.importing')}
                          </>
                        ) : (
                          <>
                            <Download className="h-4 w-4 mr-2" />
                            {isSelectionMode ? tCommon('select') : t('library.import')}
                          </>
                        )}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
