'use client';

import { use, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter, Link } from '@/lib/navigation';
import { Plus, Eye, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { useServices, useDeleteService } from '@/hooks/use-services';
import { useServiceTypes } from '@/hooks/use-service-types';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/shared/DataTable';
import { Pagination } from '@/components/shared/Pagination';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import type { ServiceResponse } from "@/types/service";

interface PageProps {
  params: Promise<{ locale: string }>;
}

export default function ServicesPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { locale } = resolvedParams;
  const t = useTranslations();
  const tCommon = useTranslations('common');
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // Delete state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedService, setSelectedService] = useState<ServiceResponse | null>(null);

  // Don't filter by organization_id to show all services
  const { data: servicesResponse, isLoading } = useServices({
    page,
    page_size: pageSize,
  });

  // Fetch service types for display
  const { data: serviceTypes } = useServiceTypes();

  // Delete mutation
  const deleteMutation = useDeleteService();

  // Helper to get service type display name
  const getServiceTypeName = (code: string | undefined) => {
    if (!code) return '-';
    const st = serviceTypes?.find(s => s.code === code);
    return st ? (locale === 'fr' ? (st.name.fr || st.name.en) : st.name.en) : code;
  };

  // Handlers
  const handleDelete = async () => {
    if (!selectedService) return;

    try {
      await deleteMutation.mutateAsync(selectedService.id);
      toast.success(t('services.deleteSuccess'));
      setDeleteDialogOpen(false);
      setSelectedService(null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('services.deleteError');
      toast.error(message);
    }
  };

  const handleViewService = (service: ServiceResponse) => {
    router.push(`/services/${service.id}`);
  };

  const columns = [
    {
      header: t('services.fields.name'),
      accessorKey: 'name' as keyof ServiceResponse,
      cell: (row: any) => (
        <Link href={`/services/${row.id}`} className="text-primary hover:underline">
          {row.name}
        </Link>
      ),
    },
    {
      header: t('services.fields.serviceType'),
      accessorKey: 'service_type' as keyof ServiceResponse,
      cell: (row: ServiceResponse) => getServiceTypeName(row.service_type),
    },
    {
      header: t('services.fields.flavors'),
      cell: (row: any) => t('services.fields.flavorCount', { count: row.flavors?.length || 0 }),
    },
    {
      header: t('common.createdAt'),
      accessorKey: 'created_at' as keyof ServiceResponse,
      cell: (row: ServiceResponse) => new Date(row.created_at).toLocaleDateString(),
    },
    {
      header: tCommon('actions'),
      cell: (row: ServiceResponse) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleViewService(row);
            }}
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedService(row);
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('services.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('services.subtitle')}</p>
        </div>
        <Button onClick={() => router.push('/services/new')} data-testid="btn-create">
          <Plus className="mr-2 h-4 w-4" />
          {t('services.createNew')}
        </Button>
      </div>

      <DataTable
        columns={columns}
        data={servicesResponse?.items || []}
        isLoading={isLoading}
        onRowClick={(row) => router.push(`/services/${row.id}`)}
        getRowId={(row) => row.id}
        emptyState={{ title: t('services.emptyStateDescription'), description: t('services.emptyStateDescription') }}
      />

      {servicesResponse && servicesResponse.total > 0 && (
        <Pagination
          page={page}
          totalPages={servicesResponse.total_pages}
          pageSize={pageSize}
          total={servicesResponse.total}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('services.deleteService')}
        description={t('services.deleteConfirm')}
        confirmText={tCommon('delete')}
        cancelText={tCommon('cancel')}
        onConfirm={handleDelete}
        variant="destructive"
      />
    </div>
  );
}
