'use client';

import { use, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { ArrowLeft, Plus, FileText, Info, Library } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { TemplateUpload, TemplateList, TemplateLibraryDialog } from '@/components/templates';

import { useService } from '@/hooks/use-services';
import { useDocumentTemplates } from '@/hooks/use-document-templates';
import { STANDARD_PLACEHOLDERS, METADATA_PLACEHOLDERS } from '@/types/document-template';

interface PageProps {
  params: Promise<{ locale: string; id: string }>;
}

export default function ServiceTemplatesPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { id: serviceId, locale } = resolvedParams;
  const t = useTranslations('templates');
  const tCommon = useTranslations('common');
  const router = useRouter();

  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [libraryDialogOpen, setLibraryDialogOpen] = useState(false);
  const [placeholderInfoOpen, setPlaceholderInfoOpen] = useState(false);

  // Fetch service and templates
  const { data: service, isLoading: serviceLoading } = useService(serviceId);
  const { data: templates = [], isLoading: templatesLoading } = useDocumentTemplates(serviceId);
  const isLoading = serviceLoading || templatesLoading;

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
            <h1 className="text-3xl font-bold">{t('title')}</h1>
            <p className="text-muted-foreground">
              {service.name} - {t('subtitle')}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setLibraryDialogOpen(true)}>
            <Library className="h-4 w-4 mr-2" />
            {t('importFromLibrary')}
          </Button>
          <Button onClick={() => setUploadDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            {t('upload')}
          </Button>
        </div>
      </div>

      {/* Placeholder Info Card */}
      <Card>
        <Collapsible open={placeholderInfoOpen} onOpenChange={setPlaceholderInfoOpen}>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Info className="h-5 w-5 text-muted-foreground" />
                  <CardTitle className="text-lg">{t('placeholderInfo.title')}</CardTitle>
                </div>
                <span className="text-sm text-muted-foreground">
                  {placeholderInfoOpen ? tCommon('collapse') : tCommon('expand')}
                </span>
              </div>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="space-y-6">
              <p className="text-muted-foreground">{t('placeholderInfo.description')}</p>

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
                <p className="text-xs text-muted-foreground italic mb-3">
                  {t('placeholderInfo.metadataNote')}
                </p>
                <div className="flex flex-wrap gap-2">
                  {METADATA_PLACEHOLDERS.map((placeholder) => (
                    <Badge key={placeholder} variant="secondary" className="font-mono">
                      {`{{${placeholder}}}`}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>

      {/* Templates List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                {t('title')}
              </CardTitle>
              <CardDescription>
                {templates.length === 0
                  ? t('noTemplates')
                  : `${templates.length} template${templates.length === 1 ? '' : 's'}`}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <TemplateList templates={templates} serviceId={serviceId} />
        </CardContent>
      </Card>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('upload')}</DialogTitle>
          </DialogHeader>
          <TemplateUpload
            serviceId={serviceId}
            onSuccess={() => setUploadDialogOpen(false)}
            onCancel={() => setUploadDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Template Library Dialog */}
      <TemplateLibraryDialog
        open={libraryDialogOpen}
        onOpenChange={setLibraryDialogOpen}
        serviceId={serviceId}
        onImportSuccess={() => setLibraryDialogOpen(false)}
      />
    </div>
  );
}
