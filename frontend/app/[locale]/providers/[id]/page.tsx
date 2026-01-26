'use client';

import type { ModelResponse } from "@/types/model";
import { use } from 'react';
import { useRouter, Link } from '@/lib/navigation';
import { useTranslations } from 'next-intl';
import { useProvider, useDeleteProvider, useVerifyProviderModels } from '@/hooks/use-providers';
import { useModels, useCreateModel } from '@/hooks/use-models';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { DataTable } from '@/components/shared/DataTable';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { ProviderModelDiscovery } from '@/components/providers/ProviderModelDiscovery';
import { toast } from 'sonner';
import { useState } from 'react';
import { Pencil, Trash2, CheckCircle, ArrowLeft, Shield, ShieldAlert, ShieldOff } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ProviderForm } from '@/components/providers/ProviderForm';
import type { DiscoveredModel } from '@/types/model';

interface PageProps {
  params: Promise<{ locale: string; id: string }>;
}

// Helper to map health_status to StatusBadge status
const getStatusBadgeType = (healthStatus: string): 'verified' | 'not-verified' | 'default' => {
  switch (healthStatus) {
    case 'available':
      return 'verified';
    case 'unavailable':
    case 'error':
      return 'not-verified';
    default:
      return 'default';
  }
};

export default function ProviderDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { id, locale } = resolvedParams;
  const t = useTranslations();
  const router = useRouter();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  // Fetch provider data
  const { data: provider, isLoading, error, refetch } = useProvider(id);

  // Fetch associated models
  const { data: modelsResponse, isLoading: modelsLoading } = useModels({
    provider_id: id,
  });

  // Mutations
  const deleteProvider = useDeleteProvider();
  const verifyModels = useVerifyProviderModels();
  const createModelMutation = useCreateModel();

  const handleImportModels = async (models: DiscoveredModel[]) => {
    const results = await Promise.allSettled(
      models.map((model) =>
        createModelMutation.mutateAsync({
          provider_id: id,
          model_name: model.model_name,
          model_identifier: model.model_identifier,
          context_length: model.context_length,
          max_generation_length: model.max_generation_length,
          tokenizer_name: model.tokenizer_name || null,
          tokenizer_class: model.tokenizer_class || null,
          is_active: true,
        })
      )
    );

    const successCount = results.filter((r) => r.status === 'fulfilled').length;
    const totalCount = models.length;

    if (successCount === totalCount) {
      toast.success(t('providers.discovery.importSuccess', { count: successCount }));
    } else if (successCount > 0) {
      toast.warning(t('providers.discovery.importPartial', { success: successCount, total: totalCount }));
    } else {
      throw new Error('All imports failed');
    }
  };

  const handleDelete = async () => {
    try {
      await deleteProvider.mutateAsync(id);
      toast.success(t('providers.deleteSuccess'));
      router.push('/providers');
    } catch (error: any) {
      toast.error(error.message || t('providers.deleteError'));
    }
  };

  const handleVerifyModels = async () => {
    try {
      await verifyModels.mutateAsync(id);
      toast.success(t('providers.verificationSuccess'));
    } catch (error: any) {
      toast.error(t('providers.verificationFailed'));
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !provider) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <p className="text-lg text-muted-foreground">{t('errors.notFound')}</p>
        <Button asChild>
          <Link href="/providers">
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common.back')}
          </Link>
        </Button>
      </div>
    );
  }

  // Model table columns
  const modelColumns = [
    {
      header: t('models.fields.name'),
      accessorKey: 'model_name' as keyof ModelResponse,
      cell: (row: any) => <span className="font-mono text-sm">{row.model_name}</span>,
    },
    {
      header: t('models.fields.modelIdentifier'),
      accessorKey: 'model_identifier' as keyof ModelResponse,
      cell: (row: any) => <span className="text-sm text-muted-foreground">{row.model_identifier}</span>,
    },
    {
      header: t('models.fields.healthStatus'),
      accessorKey: 'health_status' as keyof ModelResponse,
      cell: (row: any) => (
        <StatusBadge
          status={getStatusBadgeType(row.health_status)}
          label={t(`models.health.${row.health_status || 'unknown'}`)}
        />
      ),
    },
    {
      header: t('common.createdAt'),
      accessorKey: 'created_at' as keyof ModelResponse,
      cell: (row: any) => new Date(row.created_at).toLocaleDateString(),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center space-x-2 text-sm text-muted-foreground">
        <Link href="/providers" className="hover:text-foreground">
          {t('nav.providers')}
        </Link>
        <span>/</span>
        <span className="text-foreground">{provider.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{provider.name}</h1>
          <p className="text-muted-foreground mt-1">
            {t('providers.types.' + provider.provider_type)}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setEditDialogOpen(true)}
          >
            <Pencil className="mr-2 h-4 w-4" />
            {t('common.edit')}
          </Button>
          <Button
            variant="outline"
            onClick={handleVerifyModels}
            disabled={verifyModels.isPending}
          >
            <CheckCircle className="mr-2 h-4 w-4" />
            {verifyModels.isPending ? t('providers.verifying') : t('providers.verifyModels')}
          </Button>
          <Button
            variant="destructive"
            onClick={() => setDeleteDialogOpen(true)}
            disabled={deleteProvider.isPending}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            {t('common.delete')}
          </Button>
        </div>
      </div>

      {/* Provider Details Card */}
      <Card>
        <CardHeader>
          <CardTitle>{t('providers.viewProvider')}</CardTitle>
          <CardDescription>{t('providers.subtitle')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                {t('providers.fields.name')}
              </p>
              <p className="text-base">{provider.name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                {t('providers.fields.providerType')}
              </p>
              <Badge variant="secondary">
                {t('providers.types.' + provider.provider_type)}
              </Badge>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                {t('providers.fields.apiBaseUrl')}
              </p>
              <p className="text-base font-mono text-sm">{provider.api_base_url}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                {t('providers.fields.securityLevel')}
              </p>
              <div className="flex items-center gap-1.5 mt-1">
                {provider.security_level === 2 && <Shield className="h-4 w-4 text-green-600" />}
                {provider.security_level === 1 && <ShieldAlert className="h-4 w-4 text-yellow-600" />}
                {provider.security_level === 0 && <ShieldOff className="h-4 w-4 text-red-600" />}
                <span className="text-sm">
                  {provider.security_level === 2 && t('providers.securityLevels.secure')}
                  {provider.security_level === 1 && t('providers.securityLevels.medium')}
                  {provider.security_level === 0 && t('providers.securityLevels.insecure')}
                </span>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                {t('providers.fields.apiKey')}
              </p>
              <p className="text-base">
                {provider.api_key_exists ? '••••••••••••••••' : t('common.no')}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                {t('common.createdAt')}
              </p>
              <p className="text-base">{new Date(provider.created_at).toLocaleString()}</p>
            </div>
          </div>
          {provider.metadata && Object.keys(provider.metadata).length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">
                {t('providers.fields.metadata')}
              </p>
              <pre className="bg-muted p-3 rounded-md text-xs overflow-auto">
                {JSON.stringify(provider.metadata, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Model Discovery Card */}
      <Card>
        <CardHeader>
          <CardTitle>{t('providers.discovery.title')}</CardTitle>
          <CardDescription>{t('providers.discovery.hint')}</CardDescription>
        </CardHeader>
        <CardContent>
          <ProviderModelDiscovery providerId={id} onImport={handleImportModels} />
        </CardContent>
      </Card>

      {/* Associated Models */}
      <Card>
        <CardHeader>
          <CardTitle>{t('models.title')}</CardTitle>
          <CardDescription>
            {modelsResponse?.total || 0} {t('models.title').toLowerCase()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={modelColumns}
            data={modelsResponse?.items || []}
            isLoading={modelsLoading}
            emptyState={{ title: t('models.emptyStateDescription'), description: t('models.emptyStateDescription') }}
          />
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={handleDelete}
        title={t('providers.deleteProvider')}
        description={t('providers.deleteWarning')}
        variant="destructive"
      />

      {/* Edit Provider Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('providers.editProvider')}</DialogTitle>
          </DialogHeader>
          <ProviderForm
            provider={provider}
            onSuccess={() => {
              setEditDialogOpen(false);
              refetch();
            }}
            onCancel={() => setEditDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
