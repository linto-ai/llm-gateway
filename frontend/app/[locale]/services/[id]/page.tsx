'use client';

import { use, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import { Pencil, Trash2, ArrowLeft, Plus, FileText } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { ServiceForm } from '@/components/services/ServiceForm';
import { FlavorWizard } from '@/components/services/FlavorWizard';
import { FlavorTable } from '@/components/services/FlavorTable';
import { ServiceExecutionForm } from '@/components/services/ServiceExecutionForm';
import { ServiceAnalytics } from '@/components/services/ServiceAnalytics';
import { TemplateList } from '@/components/templates';

import { useService, useDeleteService } from '@/hooks/use-services';
import { useDocumentTemplates } from '@/hooks/use-document-templates';

interface PageProps {
  params: Promise<{ locale: string; id: string }>;
}

export default function ServiceDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { id, locale } = resolvedParams;
  const t = useTranslations('services');
  const tCommon = useTranslations('common');
  const router = useRouter();

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [addFlavorDialogOpen, setAddFlavorDialogOpen] = useState(false);

  // Fetch service data (includes flavors)
  const { data: service, isLoading, error } = useService(id);

  // Fetch document templates
  const { data: templates = [] } = useDocumentTemplates(id);

  // Mutations
  const deleteService = useDeleteService();

  const handleDelete = async () => {
    try {
      await deleteService.mutateAsync(id);
      toast.success(t('deleteSuccess'));
      router.push(`/${locale}/services`);
    } catch (error: any) {
      toast.error(error.message || t('deleteError'));
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !service) {
    const errorMessage = typeof error === 'object' && error !== null
      ? (error as any)?.message || JSON.stringify(error)
      : String(error || 'Service not found');

    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardHeader>
            <CardTitle>{tCommon('error')}</CardTitle>
            <CardDescription>
              {errorMessage}
            </CardDescription>
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
            <Link href={`/${locale}/services`}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              {tCommon('back')}
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{service.name}</h1>
            <p className="text-muted-foreground">
              {t(`types.${service.service_type}`)}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setEditDialogOpen(true)}>
            <Pencil className="h-4 w-4 mr-2" />
            {tCommon('edit')}
          </Button>
          <Button variant="destructive" onClick={() => setDeleteDialogOpen(true)}>
            <Trash2 className="h-4 w-4 mr-2" />
            {tCommon('delete')}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList>
          <TabsTrigger value="overview">{t('tabs.overview')}</TabsTrigger>
          <TabsTrigger value="flavors">{t('tabs.flavors')}</TabsTrigger>
          <TabsTrigger value="execute">{t('tabs.execute')}</TabsTrigger>
          <TabsTrigger value="analytics">{t('tabs.analytics')}</TabsTrigger>
          <TabsTrigger value="templates">{t('tabs.templates')}</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('tabs.overview')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">
                  {t('fields.name')}
                </h3>
                <p>{service.name}</p>
              </div>

              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">
                  {t('fields.serviceType')}
                </h3>
                <Badge>{t(`types.${service.service_type}`)}</Badge>
              </div>

              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">
                  {t('fields.descriptionEn')}
                </h3>
                <p className="whitespace-pre-wrap">{service.description.en}</p>
              </div>

              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">
                  {t('fields.descriptionFr')}
                </h3>
                <p className="whitespace-pre-wrap">{service.description.fr}</p>
              </div>

              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">
                  {t('fields.organizationId')}
                </h3>
                <p className="font-mono text-sm">{service.organization_id}</p>
              </div>

              <div className="flex gap-4">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-1">
                    {tCommon('createdAt')}
                  </h3>
                  <p className="text-sm">
                    {new Date(service.created_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-1">
                    {tCommon('updatedAt')}
                  </h3>
                  <p className="text-sm">
                    {new Date(service.updated_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Flavors Tab */}
        <TabsContent value="flavors" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>{t('tabs.flavors')}</CardTitle>
                  <CardDescription>
                    {t('fields.flavorCount', { count: service.flavors.length })}
                  </CardDescription>
                </div>
                <Button onClick={() => setAddFlavorDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  {t('flavors.add')}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <FlavorTable service={service} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Execute Tab */}
        <TabsContent value="execute" className="space-y-4">
          <ServiceExecutionForm service={service} />
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-4">
          <ServiceAnalytics serviceId={id} serviceName={service.name} />
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    {t('tabs.templates')}
                  </CardTitle>
                  <CardDescription>
                    {templates.length === 0
                      ? t('templatesEmpty')
                      : t('templatesCount', { count: templates.length })}
                  </CardDescription>
                </div>
                <Button variant="outline" asChild>
                  <Link href={`/${locale}/services/${id}/templates`}>
                    {t('manageTemplates')}
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <TemplateList templates={templates} serviceId={id} />
            </CardContent>
          </Card>
        </TabsContent>

      </Tabs>

      {/* Edit Service Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('editService')}</DialogTitle>
          </DialogHeader>
          <ServiceForm
            service={service}
            onSuccess={() => {
              setEditDialogOpen(false);
              toast.success(t('updateSuccess'));
            }}
            onCancel={() => setEditDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Add Flavor Dialog */}
      <Dialog open={addFlavorDialogOpen} onOpenChange={setAddFlavorDialogOpen}>
        <DialogContent className="max-w-5xl w-[90vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('flavors.add')}</DialogTitle>
          </DialogHeader>
          <FlavorWizard
            service={service}
            onSuccess={() => {
              setAddFlavorDialogOpen(false);
              toast.success(t('flavors.createSuccess'));
            }}
            onCancel={() => setAddFlavorDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('deleteService')}
        description={t('deleteConfirm')}
        onConfirm={handleDelete}
        variant="destructive"
      />
    </div>
  );
}
