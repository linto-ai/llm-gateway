'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Pencil, Trash2, Star, FlaskConical, BarChart3, Zap, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { DataTable } from '@/components/shared/DataTable';
import { EmptyState } from '@/components/shared/EmptyState';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { FlavorWizard } from './FlavorWizard';
import { FlavorTestDialog } from './FlavorTestDialog';
import { FlavorAnalytics } from './FlavorAnalytics';

import { useDeleteFlavor, useSetDefaultFlavor } from '@/hooks/use-services';
import { useModels } from '@/hooks/use-models';
import type { FlavorResponse, ServiceResponse, ProcessingMode } from '@/types/service';

// Processing mode icons mapping
const processingModeIcons: Record<ProcessingMode, typeof Zap> = {
  single_pass: Zap,
  iterative: RefreshCw,
};

interface FlavorTableProps {
  service: ServiceResponse;
}

export function FlavorTable({ service }: FlavorTableProps) {
  const t = useTranslations('services.flavors');
  const tCommon = useTranslations('common');
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedFlavor, setSelectedFlavor] = useState<FlavorResponse | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [flavorToDelete, setFlavorToDelete] = useState<FlavorResponse | null>(null);
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [analyticsDialogOpen, setAnalyticsDialogOpen] = useState(false);
  const [selectedFlavorForAction, setSelectedFlavorForAction] = useState<FlavorResponse | null>(null);

  // Fetch models to display model names
  const { data: modelsResponse } = useModels({});
  const models = modelsResponse?.items || [];

  const deleteMutation = useDeleteFlavor();
  const setDefaultMutation = useSetDefaultFlavor();

  const handleEdit = (flavor: FlavorResponse) => {
    setSelectedFlavor(flavor);
    setEditDialogOpen(true);
  };

  const handleDelete = (flavor: FlavorResponse) => {
    if (service.flavors.length === 1) {
      toast.error(t('deleteWarning'));
      return;
    }
    setFlavorToDelete(flavor);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!flavorToDelete) return;

    try {
      await deleteMutation.mutateAsync({
        serviceId: service.id,
        flavorId: flavorToDelete.id,
      });
      toast.success(t('deleteSuccess'));
      setDeleteDialogOpen(false);
      setFlavorToDelete(null);
    } catch (error: any) {
      toast.error(error.message || tCommon('error'));
    }
  };

  // Use dedicated set-default endpoint
  const handleSetDefault = async (flavor: FlavorResponse) => {
    try {
      await setDefaultMutation.mutateAsync({
        serviceId: service.id,
        flavorId: flavor.id,
      });
      toast.success(t('defaultSet'));
    } catch (error: any) {
      toast.error(t('defaultSetError'));
    }
  };

  const getModelName = (modelId: string) => {
    const model = models.find((m) => m.id === modelId);
    return model?.model_name || modelId;
  };

  const handleTest = (flavor: FlavorResponse) => {
    setSelectedFlavorForAction(flavor);
    setTestDialogOpen(true);
  };

  const handleViewStats = (flavor: FlavorResponse) => {
    setSelectedFlavorForAction(flavor);
    setAnalyticsDialogOpen(true);
  };

  if (!service.flavors || service.flavors.length === 0) {
    return (
      <EmptyState
        title={t('emptyStateDescription')}
        description=""
      />
    );
  }

  const columns = [
    {
      header: t('fields.name'),
      accessorKey: 'name' as keyof FlavorResponse,
      cell: (flavor: FlavorResponse) => (
        <div className="flex items-center gap-2">
          <span>{flavor.name}</span>
          {flavor.is_default && (
            <Badge variant="default">{t('default')}</Badge>
          )}
        </div>
      ),
    },
    {
      header: t('fields.modelId'),
      accessorKey: 'model_id' as keyof FlavorResponse,
      cell: (flavor: FlavorResponse) => getModelName(flavor.model_id),
    },
    {
      header: t('fields.temperature'),
      accessorKey: 'temperature' as keyof FlavorResponse,
      cell: (flavor: FlavorResponse) => flavor.temperature.toFixed(1),
    },
    {
      header: t('fields.processingMode'),
      accessorKey: 'processing_mode' as keyof FlavorResponse,
      cell: (flavor: FlavorResponse) => {
        const mode = (flavor.processing_mode || 'iterative') as ProcessingMode;
        const Icon = processingModeIcons[mode] || RefreshCw;
        return (
          <Badge variant="outline" className="gap-1">
            <Icon className="h-3 w-3" />
            {t(`processingMode.${mode}`)}
          </Badge>
        );
      },
    },
    {
      header: t('fields.priority'),
      accessorKey: 'priority' as keyof FlavorResponse,
      cell: (flavor: FlavorResponse) => flavor.priority || 0,
    },
    {
      header: t('fields.status'),
      accessorKey: 'is_active' as keyof FlavorResponse,
      cell: (flavor: FlavorResponse) => (
        <Badge variant={flavor.is_active ? 'success' : 'secondary'}>
          {flavor.is_active ? t('active') : t('inactive')}
        </Badge>
      ),
    },
    {
      header: tCommon('actions'),
      cell: (flavor: FlavorResponse) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              {tCommon('actions')}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => handleEdit(flavor)}>
              <Pencil className="mr-2 h-4 w-4" />
              {tCommon('edit')}
            </DropdownMenuItem>
            {!flavor.is_default && (
              <DropdownMenuItem onClick={() => handleSetDefault(flavor)}>
                <Star className="mr-2 h-4 w-4" />
                {t('setDefault')}
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => handleTest(flavor)}>
              <FlaskConical className="mr-2 h-4 w-4" />
              {t('test')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleViewStats(flavor)}>
              <BarChart3 className="mr-2 h-4 w-4" />
              {t('viewStats')}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => handleDelete(flavor)}
              className="text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {tCommon('delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        data={service.flavors}
        getRowId={(flavor) => flavor.id}
      />

      {/* Edit Flavor Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-5xl w-[90vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('edit')}</DialogTitle>
          </DialogHeader>
          {selectedFlavor && (
            <FlavorWizard
              service={service}
              flavor={selectedFlavor}
              onSuccess={() => {
                setEditDialogOpen(false);
                setSelectedFlavor(null);
                toast.success(t('updateSuccess'));
              }}
              onCancel={() => {
                setEditDialogOpen(false);
                setSelectedFlavor(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('delete')}
        description={t('deleteConfirm')}
        onConfirm={confirmDelete}
        variant="destructive"
      />

      {/* Test Flavor Dialog */}
      {selectedFlavorForAction && (
        <FlavorTestDialog
          open={testDialogOpen}
          onOpenChange={setTestDialogOpen}
          flavorId={selectedFlavorForAction.id}
          flavorName={selectedFlavorForAction.name}
        />
      )}

      {/* Analytics Dialog */}
      {selectedFlavorForAction && (
        <Dialog open={analyticsDialogOpen} onOpenChange={setAnalyticsDialogOpen}>
          <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{t('analyticsTitle')}</DialogTitle>
            </DialogHeader>
            <FlavorAnalytics
              flavorId={selectedFlavorForAction.id}
              flavorName={selectedFlavorForAction.name}
            />
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
