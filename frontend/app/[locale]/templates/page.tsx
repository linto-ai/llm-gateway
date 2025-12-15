'use client';

import { use, useState, useMemo } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Plus, Filter, FileText, Info } from 'lucide-react';

import { useDocumentTemplates } from '@/hooks/use-document-templates';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';

import { TemplateList } from '@/components/templates/TemplateList';
import { TemplateUpload } from '@/components/templates/TemplateUpload';
import { TemplateEditDialog } from '@/components/templates/TemplateEditDialog';
import { filterTemplatesByScope, sortTemplatesByScope } from '@/lib/template-utils';
import {
  STANDARD_PLACEHOLDERS,
  METADATA_PLACEHOLDERS,
} from '@/types/document-template';
import type { DocumentTemplate, TemplateScope } from '@/types/document-template';

interface PageProps {
  params: Promise<{ locale: string }>;
}

export default function TemplatesPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { locale } = resolvedParams;
  const t = useTranslations('templates');
  const tCommon = useTranslations('common');

  // State
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<DocumentTemplate | null>(null);
  const [scopeFilter, setScopeFilter] = useState<TemplateScope | 'all'>('all');
  const [showPlaceholderInfo, setShowPlaceholderInfo] = useState(false);

  // Fetch ALL templates (admin mode - system + org + user)
  const { data: templates, isLoading, isFetching, refetch } = useDocumentTemplates({
    include_all: true,
  });

  // Show loading state for initial fetch
  const showLoading = isLoading || (isFetching && !templates);

  // Filter and sort templates - use useMemo to ensure proper re-rendering when data changes
  const filteredTemplates = useMemo(
    () => sortTemplatesByScope(filterTemplatesByScope(templates ?? [], scopeFilter)),
    [templates, scopeFilter]
  );

  // Handle upload success
  const handleUploadSuccess = () => {
    setUploadDialogOpen(false);
    refetch();
  };

  // Handle edit
  const handleEdit = (template: DocumentTemplate) => {
    setSelectedTemplate(template);
    setEditDialogOpen(true);
  };

  // Handle edit success
  const handleEditSuccess = () => {
    refetch();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('title')}</h1>
          <p className="text-muted-foreground mt-1">{t('subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowPlaceholderInfo(true)}
          >
            <Info className="h-4 w-4 mr-2" />
            {t('placeholderInfo.title')}
          </Button>
          <Button onClick={() => setUploadDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('upload')}
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Label>{t('filters.scope')}</Label>
          <Select
            value={scopeFilter}
            onValueChange={(value) => setScopeFilter(value as TemplateScope | 'all')}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('filters.allScopes')}</SelectItem>
              <SelectItem value="system">{t('scope.system')}</SelectItem>
              <SelectItem value="organization">{t('scope.organization')}</SelectItem>
              <SelectItem value="user">{t('scope.user')}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Template count */}
        <div className="text-sm text-muted-foreground">
          {t('filters.count', { count: filteredTemplates.length })}
        </div>
      </div>

      {/* Template List */}
      <Card>
        <CardContent className="p-0">
          {showLoading ? (
            <div className="p-6 space-y-4">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <TemplateList
              templates={filteredTemplates}
              onEdit={handleEdit}
              showScope={true}
              showDefaultColumn={true}
              showGlobalDefaultAction={true}
            />
          )}
        </CardContent>
      </Card>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('upload')}</DialogTitle>
            <DialogDescription>
              {t('uploadDescription')}
            </DialogDescription>
          </DialogHeader>
          <TemplateUpload
            onSuccess={handleUploadSuccess}
            onCancel={() => setUploadDialogOpen(false)}
            showDefaultOption={false}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <TemplateEditDialog
        template={selectedTemplate}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        onSuccess={handleEditSuccess}
      />

      {/* Placeholder Info Dialog */}
      <Dialog open={showPlaceholderInfo} onOpenChange={setShowPlaceholderInfo}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {t('placeholderInfo.title')}
            </DialogTitle>
            <DialogDescription>
              {t('placeholderInfo.description')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            {/* Standard Placeholders */}
            <div>
              <h4 className="font-medium mb-2">{t('placeholderInfo.standard')}</h4>
              <p className="text-sm text-muted-foreground mb-3">
                {t('placeholderInfo.standardDescription')}
              </p>
              <div className="flex flex-wrap gap-2">
                {STANDARD_PLACEHOLDERS.map((placeholder) => (
                  <Badge key={placeholder} variant="outline" className="font-mono">
                    {`{{${placeholder}}}`}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Metadata Placeholders */}
            <div>
              <h4 className="font-medium mb-2">{t('placeholderInfo.metadata')}</h4>
              <p className="text-sm text-muted-foreground mb-3">
                {t('placeholderInfo.metadataDescription')}
              </p>
              <div className="flex flex-wrap gap-2">
                {METADATA_PLACEHOLDERS.map((placeholder) => (
                  <Badge key={placeholder} variant="secondary" className="font-mono">
                    {`{{${placeholder}}}`}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Custom Placeholders Note */}
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                {t('placeholderInfo.metadataNote')}
              </AlertDescription>
            </Alert>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
