'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import { Download, Trash2, Star, FileText, MoreHorizontal } from 'lucide-react';
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
  useDownloadDocumentTemplate,
} from '@/hooks/use-document-templates';
import type { DocumentTemplate } from '@/types/document-template';
import { getPlaceholderName } from '@/types/document-template';

interface TemplateListProps {
  templates: DocumentTemplate[];
  serviceId: string;
}

/**
 * Table displaying document templates with actions.
 */
export function TemplateList({ templates, serviceId }: TemplateListProps) {
  const t = useTranslations('templates');

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState<DocumentTemplate | null>(null);

  const deleteMutation = useDeleteDocumentTemplate();
  const setDefaultMutation = useSetDefaultDocumentTemplate();
  const downloadMutation = useDownloadDocumentTemplate();

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

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

  // Handle set as default
  const handleSetDefault = async (template: DocumentTemplate) => {
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
            <TableHead>{t('table.fileName')}</TableHead>
            <TableHead>{t('table.size')}</TableHead>
            <TableHead>{t('table.placeholders')}</TableHead>
            <TableHead>{t('table.default')}</TableHead>
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
                  {template.name}
                </div>
                {template.description && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {template.description}
                  </p>
                )}
              </TableCell>
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
                    <DropdownMenuItem onClick={() => handleDownload(template)}>
                      <Download className="h-4 w-4 mr-2" />
                      {t('download')}
                    </DropdownMenuItem>
                    {!template.is_default && (
                      <DropdownMenuItem onClick={() => handleSetDefault(template)}>
                        <Star className="h-4 w-4 mr-2" />
                        {t('setDefault')}
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
