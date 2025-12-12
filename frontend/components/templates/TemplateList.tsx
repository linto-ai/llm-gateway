'use client';

import { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { toast } from 'sonner';
import { Download, Trash2, Star, FileText, MoreHorizontal, Pencil } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';

import {
  useDeleteDocumentTemplate,
  useSetDefaultDocumentTemplate,
  useSetGlobalDefaultDocumentTemplate,
  useDownloadDocumentTemplate,
} from '@/hooks/use-document-templates';
import type { DocumentTemplate, TemplateScope } from '@/types/document-template';
import { getPlaceholderName } from '@/types/document-template';
import {
  getLocalizedName,
  getLocalizedDescription,
  getScopeBadgeVariant,
  formatFileSize,
} from '@/lib/template-utils';

interface TemplateListProps {
  templates: DocumentTemplate[];
  serviceId?: string;
  onEdit?: (template: DocumentTemplate) => void;
  showScope?: boolean;
  /** Whether to show the "Default" column. Only relevant in service context. */
  showDefaultColumn?: boolean;
  /** Whether to show "Set as global default" action for system templates */
  showGlobalDefaultAction?: boolean;
}

/**
 * Table displaying document templates with actions.
 */
export function TemplateList({
  templates,
  serviceId,
  onEdit,
  showScope = true,
  showDefaultColumn = true,
  showGlobalDefaultAction = false,
}: TemplateListProps) {
  const t = useTranslations('templates');
  const locale = useLocale();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState<DocumentTemplate | null>(null);

  const deleteMutation = useDeleteDocumentTemplate();
  const setDefaultMutation = useSetDefaultDocumentTemplate();
  const setGlobalDefaultMutation = useSetGlobalDefaultDocumentTemplate();
  const downloadMutation = useDownloadDocumentTemplate();

  // Handle delete
  const handleDelete = async () => {
    if (!templateToDelete) return;

    try {
      await deleteMutation.mutateAsync(templateToDelete.id);
      toast.success(t('deleteSuccess'));
      setDeleteDialogOpen(false);
      setTemplateToDelete(null);
    } catch (error: any) {
      toast.error(error.message || t('deleteError'));
    }
  };

  // Handle set as default for a service
  const handleSetDefault = async (template: DocumentTemplate) => {
    if (!serviceId) return;

    try {
      await setDefaultMutation.mutateAsync({
        templateId: template.id,
        serviceId,
      });
      toast.success(t('setDefaultSuccess'));
    } catch (error: any) {
      toast.error(error.message || t('setDefaultError'));
    }
  };

  // Handle set as global default
  const handleSetGlobalDefault = async (template: DocumentTemplate) => {
    try {
      await setGlobalDefaultMutation.mutateAsync(template.id);
      toast.success(t('setGlobalDefaultSuccess'));
    } catch (error: any) {
      toast.error(error.message || t('setGlobalDefaultError'));
    }
  };

  // Handle download
  const handleDownload = async (template: DocumentTemplate) => {
    try {
      await downloadMutation.mutateAsync({
        id: template.id,
        fileName: template.file_name,
      });
    } catch (error: any) {
      toast.error(error.message || 'Download failed');
    }
  };

  // Get scope label
  const getScopeLabel = (scope: TemplateScope): string => {
    return t(`scope.${scope}`);
  };

  if (templates.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <p className="text-lg font-medium">{t('noTemplates')}</p>
        <p className="text-sm text-muted-foreground">{t('noTemplatesDescription')}</p>
      </div>
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t('table.name')}</TableHead>
            {showScope && <TableHead>{t('table.scope')}</TableHead>}
            <TableHead>{t('table.fileName')}</TableHead>
            <TableHead>{t('table.size')}</TableHead>
            <TableHead>{t('table.placeholders')}</TableHead>
            {showDefaultColumn && <TableHead>{t('table.default')}</TableHead>}
            <TableHead>{t('table.createdAt')}</TableHead>
            <TableHead className="text-right">{t('table.actions')}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {templates.map((template) => (
            <TableRow key={template.id}>
              <TableCell className="font-medium">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-blue-500" />
                  <div>
                    <div>{getLocalizedName(template, locale)}</div>
                    {/* Show alternate language name if available */}
                    {locale === 'fr' && template.name_en && (
                      <div className="text-xs text-muted-foreground">
                        EN: {template.name_en}
                      </div>
                    )}
                    {locale === 'en' && template.name_fr !== getLocalizedName(template, locale) && (
                      <div className="text-xs text-muted-foreground">
                        FR: {template.name_fr}
                      </div>
                    )}
                  </div>
                </div>
                {getLocalizedDescription(template, locale) && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {getLocalizedDescription(template, locale)}
                  </p>
                )}
              </TableCell>
              {showScope && (
                <TableCell>
                  <Badge variant={getScopeBadgeVariant(template.scope)}>
                    {getScopeLabel(template.scope)}
                  </Badge>
                </TableCell>
              )}
              <TableCell className="text-sm text-muted-foreground">
                {template.file_name}
              </TableCell>
              <TableCell className="text-sm">
                {formatFileSize(template.file_size)}
              </TableCell>
              <TableCell>
                {template.placeholders && template.placeholders.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {template.placeholders.slice(0, 3).map((placeholder) => (
                      <Badge key={placeholder} variant="outline" className="text-xs font-mono" title={placeholder}>
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
                  <span className="text-sm text-muted-foreground">{t('noPlaceholders')}</span>
                )}
              </TableCell>
              {showDefaultColumn && (
                <TableCell>
                  {template.is_default ? (
                    <Badge className="gap-1">
                      <Star className="h-3 w-3" />
                      {t('isDefault')}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </TableCell>
              )}
              <TableCell className="text-sm text-muted-foreground">
                {formatDistanceToNow(new Date(template.created_at), { addSuffix: true })}
              </TableCell>
              <TableCell className="text-right">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {onEdit && (
                      <DropdownMenuItem onClick={() => onEdit(template)}>
                        <Pencil className="h-4 w-4 mr-2" />
                        {t('edit')}
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem onClick={() => handleDownload(template)}>
                      <Download className="h-4 w-4 mr-2" />
                      {t('download')}
                    </DropdownMenuItem>
                    {serviceId && !template.is_default && (
                      <DropdownMenuItem onClick={() => handleSetDefault(template)}>
                        <Star className="h-4 w-4 mr-2" />
                        {t('setDefault')}
                      </DropdownMenuItem>
                    )}
                    {showGlobalDefaultAction && template.scope === 'system' && !template.is_default && (
                      <DropdownMenuItem onClick={() => handleSetGlobalDefault(template)}>
                        <Star className="h-4 w-4 mr-2" />
                        {t('setGlobalDefault')}
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="text-destructive"
                      onClick={() => {
                        setTemplateToDelete(template);
                        setDeleteDialogOpen(true);
                      }}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      {t('delete')}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('delete')}
        description={t('deleteConfirm')}
        onConfirm={handleDelete}
        variant="destructive"
      />
    </>
  );
}
