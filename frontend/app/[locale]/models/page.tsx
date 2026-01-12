'use client';

import { use, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter, Link } from '@/lib/navigation';
import { Plus, Shield, ShieldAlert, ShieldOff, Eye, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { useModels, useDeleteModel } from '@/hooks/use-models';
import { useProviders } from '@/hooks/use-providers';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { DataTable } from '@/components/shared/DataTable';
import { Pagination } from '@/components/shared/Pagination';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import type { HealthStatus, ModelResponse } from '@/types/model';

interface PageProps {
  params: Promise<{ locale: string }>;
}

export default function ModelsPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { locale } = resolvedParams;
  const t = useTranslations();
  const tCommon = useTranslations('common');
  const router = useRouter();

  // Filters state
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [providerId, setProviderId] = useState<string>('');
  const [healthStatus, setHealthStatus] = useState<HealthStatus | ''>('');

  // Delete state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<ModelResponse | null>(null);

  // Fetch models with filters
  const { data: modelsResponse, isLoading } = useModels({
    provider_id: providerId || undefined,
    health_status: healthStatus || undefined,
    page,
    page_size: pageSize,
  });

  // Fetch providers for filter dropdown
  // Don't filter by organization_id to show all providers
  const { data: providersResponse } = useProviders({
    page_size: 100,
  });

  // Delete mutation
  const deleteMutation = useDeleteModel();

  // Handlers
  const handleDelete = async () => {
    if (!selectedModel) return;

    try {
      await deleteMutation.mutateAsync(selectedModel.id);
      toast.success(t('models.deleteSuccess'));
      setDeleteDialogOpen(false);
      setSelectedModel(null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('models.deleteError');
      toast.error(message);
    }
  };

  const handleViewModel = (model: ModelResponse) => {
    router.push(`/models/${model.id}`);
  };

  const columns = [
    {
      header: t('models.fields.name'),
      accessorKey: 'model_name' as keyof ModelResponse,
      cell: (row: any) => (
        <Link
          href={`/models/${row.id}`}
          className="font-mono text-sm text-primary hover:underline"
        >
          {row.model_name}
        </Link>
      ),
    },
    {
      header: t('models.fields.modelIdentifier'),
      accessorKey: 'model_identifier' as keyof ModelResponse,
      cell: (row: any) => <span className="text-sm text-muted-foreground">{row.model_identifier}</span>,
    },
    {
      header: t('models.fields.providerId'),
      accessorKey: 'provider_id' as keyof ModelResponse,
      cell: (row: any) => row.provider_name || row.provider_id.slice(0, 8),
    },
    {
      header: t('models.fields.healthStatus'),
      accessorKey: 'health_status' as keyof ModelResponse,
      cell: (row: any) => {
        const getStatusType = (status: string): 'verified' | 'not-verified' | 'default' => {
          switch (status) {
            case 'available': return 'verified';
            case 'unavailable':
            case 'error': return 'not-verified';
            default: return 'default';
          }
        };
        return (
          <StatusBadge
            status={getStatusType(row.health_status)}
            label={row.health_status ? t(`models.health.${row.health_status}`) : t('models.notVerified')}
          />
        );
      },
    },
    {
      header: t('models.fields.securityLevel'),
      accessorKey: 'security_level' as keyof ModelResponse,
      cell: (row: any) => {
        const level = row.security_level;
        if (!level) return <span className="text-muted-foreground">-</span>;

        const config: Record<string, { icon: typeof Shield; color: string }> = {
          secure: { icon: Shield, color: 'text-green-600' },
          sensitive: { icon: ShieldAlert, color: 'text-yellow-600' },
          insecure: { icon: ShieldOff, color: 'text-red-600' },
        };
        const { icon: Icon, color } = config[level] || { icon: Shield, color: 'text-muted-foreground' };

        return (
          <div className="flex items-center gap-1.5">
            <Icon className={`h-4 w-4 ${color}`} />
            <span className="text-sm">{t(`models.securityLevels.${level}`)}</span>
          </div>
        );
      },
    },
    {
      header: t('common.createdAt'),
      accessorKey: 'created_at' as keyof ModelResponse,
      cell: (row: ModelResponse) => new Date(row.created_at).toLocaleDateString(),
    },
    {
      header: tCommon('actions'),
      cell: (row: ModelResponse) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleViewModel(row);
            }}
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedModel(row);
              setDeleteDialogOpen(true);
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  const handleRowClick = (row: any) => {
    router.push(`/models/${row.id}`);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('models.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('models.subtitle')}</p>
        </div>
        <Button onClick={() => router.push('/models/new')} data-testid="btn-create">
          <Plus className="mr-2 h-4 w-4" />
          {t('models.createNew')}
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Select value={providerId || "all"} onValueChange={(val) => setProviderId(val === "all" ? "" : val)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder={t('models.fields.providerId')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('common.all')}</SelectItem>
            {providersResponse?.items.map((provider) => (
              <SelectItem key={provider.id} value={provider.id}>
                {provider.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={healthStatus || "all"} onValueChange={(val) => setHealthStatus(val === "all" ? "" : val as HealthStatus)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder={t('models.fields.healthStatus')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('common.all')}</SelectItem>
            <SelectItem value="available">{t('models.health.available')}</SelectItem>
            <SelectItem value="unavailable">{t('models.health.unavailable')}</SelectItem>
            <SelectItem value="unknown">{t('models.health.unknown')}</SelectItem>
            <SelectItem value="error">{t('models.health.error')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={modelsResponse?.items || []}
        isLoading={isLoading}
        onRowClick={handleRowClick}
        getRowId={(row) => row.id}
        emptyState={{
          title: t('models.emptyStateTitle'),
          description: t('models.emptyStateDescription'),
        }}
      />

      {/* Pagination */}
      {modelsResponse && modelsResponse.total > 0 && (
        <Pagination
          page={page}
          totalPages={modelsResponse.total_pages}
          pageSize={pageSize}
          total={modelsResponse.total}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('models.deleteModel')}
        description={t('models.deleteConfirm')}
        confirmText={tCommon('delete')}
        cancelText={tCommon('cancel')}
        onConfirm={handleDelete}
        variant="destructive"
      />
    </div>
  );
}
