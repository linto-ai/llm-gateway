'use client';

import { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Eye, Trash2, Zap, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { DataTable } from '@/components/shared/DataTable';
import { EmptyState } from '@/components/shared/EmptyState';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { PresetForm } from './PresetForm';
import { useDeletePreset } from '@/hooks/use-presets';
import { useServiceTypes } from '@/hooks/use-service-types';
import type { FlavorPreset } from '@/types/preset';
import type { ProcessingMode } from '@/types/service';

interface PresetTableProps {
  presets: FlavorPreset[];
  isLoading: boolean;
}

const modeIcons: Record<ProcessingMode, typeof Zap> = {
  single_pass: Zap,
  iterative: RefreshCw,
};

export function PresetTable({ presets, isLoading }: PresetTableProps) {
  const t = useTranslations('presets');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<FlavorPreset | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [presetToDelete, setPresetToDelete] = useState<FlavorPreset | null>(null);

  const deleteMutation = useDeletePreset();
  const { data: serviceTypes } = useServiceTypes();

  // Helper to get service type display name
  const getServiceTypeName = (code: string | undefined) => {
    if (!code) return '-';
    const st = serviceTypes?.find(s => s.code === code);
    return st ? (locale === 'fr' ? (st.name.fr || st.name.en) : st.name.en) : code;
  };

  const handleEdit = (preset: FlavorPreset) => {
    setSelectedPreset(preset);
    setEditDialogOpen(true);
  };

  const handleDelete = (preset: FlavorPreset) => {
    if (preset.is_system) {
      toast.error(t('cannotDeleteSystem'));
      return;
    }
    setPresetToDelete(preset);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!presetToDelete) return;

    try {
      await deleteMutation.mutateAsync(presetToDelete.id);
      toast.success(t('deleteSuccess'));
      setDeleteDialogOpen(false);
      setPresetToDelete(null);
    } catch (error: any) {
      toast.error(error.message || tCommon('error'));
    }
  };

  if (!isLoading && presets.length === 0) {
    return (
      <EmptyState
        title={t('emptyState')}
        description={t('emptyStateDescription')}
      />
    );
  }

  const columns = [
    {
      header: t('fields.name'),
      accessorKey: 'name' as keyof FlavorPreset,
      cell: (preset: FlavorPreset) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{preset.name}</span>
          {preset.is_system && (
            <Badge variant="secondary">{t('system')}</Badge>
          )}
        </div>
      ),
    },
    {
      header: t('fields.serviceType'),
      accessorKey: 'service_type' as keyof FlavorPreset,
      cell: (preset: FlavorPreset) => getServiceTypeName(preset.service_type),
    },
    {
      header: t('fields.description'),
      accessorKey: 'description_en' as keyof FlavorPreset,
      cell: (preset: FlavorPreset) => (
        <span className="text-sm text-muted-foreground line-clamp-1">
          {locale === 'fr' ? preset.description_fr : preset.description_en}
        </span>
      ),
    },
    {
      header: t('fields.processingMode'),
      accessorKey: 'config' as keyof FlavorPreset,
      cell: (preset: FlavorPreset) => {
        const mode = preset.config.processing_mode as ProcessingMode;
        const Icon = modeIcons[mode] || RefreshCw;
        return (
          <Badge variant="outline" className="gap-1">
            <Icon className="h-3 w-3" />
            {mode.replace('_', ' ')}
          </Badge>
        );
      },
    },
    {
      header: tCommon('actions'),
      cell: (preset: FlavorPreset) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleEdit(preset);
            }}
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(preset);
            }}
            disabled={preset.is_system}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        data={presets}
        getRowId={(preset) => preset.id}
        isLoading={isLoading}
      />

      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('editTitle')}</DialogTitle>
          </DialogHeader>
          {selectedPreset && (
            <PresetForm
              preset={selectedPreset}
              onSuccess={() => {
                setEditDialogOpen(false);
                setSelectedPreset(null);
                toast.success(t('updateSuccess'));
              }}
              onCancel={() => {
                setEditDialogOpen(false);
                setSelectedPreset(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('deleteTitle')}
        description={t('deleteConfirm')}
        onConfirm={confirmDelete}
        variant="destructive"
      />
    </>
  );
}
