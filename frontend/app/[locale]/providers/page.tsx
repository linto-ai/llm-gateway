'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from '@/lib/navigation';
import { useParams } from 'next/navigation';
import { Plus, Eye, Edit, Trash2, CheckCircle, Shield, ShieldAlert, ShieldOff } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DataTable, DataTableColumn } from '@/components/shared/DataTable';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { ProviderForm } from '@/components/providers/ProviderForm';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

import { useProviders, useDeleteProvider, useVerifyProviderModels } from '@/hooks/use-providers';
import type { ProviderResponse, ProviderType, SecurityLevel } from '@/types/provider';
import { PROVIDER_TYPES, SECURITY_LEVELS } from '@/lib/constants';

export default function ProvidersPage() {
  const t = useTranslations('providers');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const params = useParams();
  const locale = params.locale as string;

  // State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [providerType, setProviderType] = useState<ProviderType | ''>('');
  const [securityLevel, setSecurityLevel] = useState<SecurityLevel | ''>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<ProviderResponse | null>(null);

  // Queries and mutations
  // Don't filter by organization_id to show all providers (including those with null organization_id)
  const { data, isLoading, error } = useProviders({
    provider_type: providerType || undefined,
    security_level: securityLevel || undefined,
    page,
    page_size: pageSize,
  });

  const deleteMutation = useDeleteProvider();
  const verifyMutation = useVerifyProviderModels();

  // Handlers
  const handleDelete = async () => {
    if (!selectedProvider) return;

    try {
      await deleteMutation.mutateAsync(selectedProvider.id);
      toast.success(t('deleteSuccess'));
      setDeleteDialogOpen(false);
      setSelectedProvider(null);
    } catch (error: any) {
      toast.error(error.message || t('deleteError'));
    }
  };

  const handleVerify = async (providerId: string) => {
    try {
      await verifyMutation.mutateAsync(providerId);
      toast.success(t('verificationSuccess'));
    } catch (error: any) {
      toast.error(error.message || t('verificationFailed'));
    }
  };

  const handleViewProvider = (provider: ProviderResponse) => {
    router.push(`/providers/${provider.id}`);
  };

  // Table columns
  const columns: DataTableColumn<ProviderResponse>[] = [
    {
      header: t('fields.name'),
      accessorKey: 'name',
      cell: (row) => <span className="font-medium">{row.name}</span>,
    },
    {
      header: t('fields.providerType'),
      accessorKey: 'provider_type',
      cell: (row) => t(`types.${row.provider_type}`),
    },
    {
      header: t('fields.securityLevel'),
      cell: (row) => {
        const level = row.security_level;
        const config: Record<string, { icon: typeof Shield; color: string }> = {
          secure: { icon: Shield, color: 'text-green-600' },
          sensitive: { icon: ShieldAlert, color: 'text-yellow-600' },
          insecure: { icon: ShieldOff, color: 'text-red-600' },
        };
        const { icon: Icon, color } = config[level] || { icon: Shield, color: 'text-muted-foreground' };

        return (
          <div className="flex items-center gap-1.5">
            <Icon className={`h-4 w-4 ${color}`} />
            <span className="text-sm">{t(`securityLevels.${level}`)}</span>
          </div>
        );
      },
    },
    {
      header: t('fields.apiBaseUrl'),
      accessorKey: 'api_base_url',
      cell: (row) => <span className="text-sm text-muted-foreground">{row.api_base_url}</span>,
    },
    {
      header: tCommon('actions'),
      cell: (row) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleViewProvider(row);
            }}
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleVerify(row.id);
            }}
            disabled={verifyMutation.isPending}
          >
            <CheckCircle className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedProvider(row);
              setDeleteDialogOpen(true);
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
          <p className="text-muted-foreground">{t('subtitle')}</p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)} data-testid="btn-create">
          <Plus className="mr-2 h-4 w-4" />
          {t('createNew')}
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Input
          placeholder={tCommon('search')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-xs"
        />
        <Select value={providerType || "all"} onValueChange={(val) => setProviderType(val === "all" ? "" : val as ProviderType)}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder={t('fields.providerType')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{tCommon('all')}</SelectItem>
            {PROVIDER_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {t(`types.${type}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={securityLevel || "all"} onValueChange={(val) => setSecurityLevel(val === "all" ? "" : val as SecurityLevel)}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder={t('fields.securityLevel')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{tCommon('all')}</SelectItem>
            {SECURITY_LEVELS.map((level) => (
              <SelectItem key={level} value={level}>
                {t(`securityLevels.${level}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Data Table */}
      <DataTable
        data={data?.items || []}
        columns={columns}
        isLoading={isLoading}
        emptyState={{
          title: tCommon('noResults'),
          description: t('emptyStateDescription'),
          actionLabel: t('createNew'),
          onAction: () => setCreateDialogOpen(true),
        }}
        pagination={
          data
            ? {
                page,
                pageSize,
                total: data.total,
                totalPages: data.total_pages,
                onPageChange: setPage,
                onPageSizeChange: setPageSize,
              }
            : undefined
        }
        getRowId={(row) => row.id}
        onRowClick={handleViewProvider}
      />

      {/* Create Provider Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('createNew')}</DialogTitle>
          </DialogHeader>
          <ProviderForm
            onSuccess={() => {
              setCreateDialogOpen(false);
              toast.success(t('createSuccess'));
            }}
            onCancel={() => setCreateDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('deleteProvider')}
        description={t('deleteConfirm')}
        confirmText={tCommon('delete')}
        cancelText={tCommon('cancel')}
        onConfirm={handleDelete}
        variant="destructive"
      />
    </div>
  );
}
