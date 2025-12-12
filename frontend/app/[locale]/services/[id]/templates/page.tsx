'use client';

import { use, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import { toast } from 'sonner';
import { ArrowLeft, FileText, Check, X, Library } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { TemplateLibraryDialog } from '@/components/templates';

import { useService, useUpdateService } from '@/hooks/use-services';
import { useDocumentTemplate, useDocumentTemplates } from '@/hooks/use-document-templates';
import { getLocalizedName, getLocalizedDescription } from '@/lib/template-utils';

interface PageProps {
  params: Promise<{ locale: string; id: string }>;
}

export default function ServiceTemplatesPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { id: serviceId, locale } = resolvedParams;
  const t = useTranslations('services');
  const tTemplates = useTranslations('templates');
  const tCommon = useTranslations('common');

  const [libraryDialogOpen, setLibraryDialogOpen] = useState(false);
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);

  // Fetch service
  const { data: service, isLoading: serviceLoading, refetch: refetchService } = useService(serviceId);

  // Fetch current default template if set
  const { data: currentTemplate, isLoading: templateLoading } = useDocumentTemplate(
    service?.default_template_id ?? undefined
  );

  // Update service mutation
  const updateService = useUpdateService();

  const isLoading = serviceLoading || templateLoading;

  // Handle template selection from library
  const handleTemplateSelect = async (templateId: string) => {
    try {
      await updateService.mutateAsync({
        id: serviceId,
        data: { default_template_id: templateId },
      });
      toast.success(t('defaultTemplateSet'));
      setLibraryDialogOpen(false);
      refetchService();
    } catch (error: any) {
      toast.error(error.message || tCommon('error'));
    }
  };

  // Handle remove default template
  const handleRemoveDefault = async () => {
    try {
      await updateService.mutateAsync({
        id: serviceId,
        data: { default_template_id: null },
      });
      toast.success(t('defaultTemplateRemoved'));
      setRemoveDialogOpen(false);
      refetchService();
    } catch (error: any) {
      toast.error(error.message || tCommon('error'));
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <LoadingSpinner />
      </div>
    );
  }

  if (!service) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardHeader>
            <CardTitle>{tCommon('error')}</CardTitle>
            <CardDescription>Service not found</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/${locale}/services/${serviceId}`}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              {tCommon('back')}
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{t('tabs.templates')}</h1>
            <p className="text-muted-foreground">
              {service.name} - {t('selectDefaultTemplate')}
            </p>
          </div>
        </div>
      </div>

      {/* Current Default Template */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {t('currentDefault')}
          </CardTitle>
          <CardDescription>
            {tTemplates('uploadDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {currentTemplate ? (
            <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/30">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-lg bg-primary/10">
                  <FileText className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 className="font-medium">{getLocalizedName(currentTemplate, locale)}</h3>
                  {getLocalizedDescription(currentTemplate, locale) && (
                    <p className="text-sm text-muted-foreground">
                      {getLocalizedDescription(currentTemplate, locale)}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className="text-xs">
                      {currentTemplate.file_name}
                    </Badge>
                    {currentTemplate.placeholders && currentTemplate.placeholders.length > 0 && (
                      <Badge variant="secondary" className="text-xs">
                        {currentTemplate.placeholders.length} placeholders
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setLibraryDialogOpen(true)}
                >
                  {t('changeDefault')}
                </Button>
                <Button
                  variant="ghost"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setRemoveDialogOpen(true)}
                >
                  <X className="h-4 w-4 mr-1" />
                  {t('removeDefault')}
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="p-4 rounded-full bg-muted mb-4">
                <FileText className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="font-medium mb-1">{t('noDefaultTemplate')}</h3>
              <p className="text-sm text-muted-foreground mb-4">
                {t('templatesEmpty')}
              </p>
              <Button onClick={() => setLibraryDialogOpen(true)}>
                <Library className="h-4 w-4 mr-2" />
                {t('selectDefaultTemplate')}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="border-dashed">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <FileText className="h-5 w-5 text-blue-500" />
            </div>
            <div className="text-sm text-muted-foreground">
              <p className="font-medium text-foreground mb-1">
                {tTemplates('placeholderInfo.title')}
              </p>
              <p>
                {tTemplates('placeholderInfo.description')}
              </p>
              <Button
                variant="link"
                className="px-0 h-auto mt-2"
                asChild
              >
                <Link href={`/${locale}/templates`}>
                  {tTemplates('title')} →
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Template Library Dialog */}
      <TemplateLibraryDialog
        open={libraryDialogOpen}
        onOpenChange={setLibraryDialogOpen}
        onSelect={(template) => handleTemplateSelect(template.id)}
      />

      {/* Remove Confirmation Dialog */}
      <ConfirmDialog
        open={removeDialogOpen}
        onOpenChange={setRemoveDialogOpen}
        title={t('removeDefault')}
        description={t('removeDefaultConfirm')}
        onConfirm={handleRemoveDefault}
        variant="destructive"
      />
    </div>
  );
}
