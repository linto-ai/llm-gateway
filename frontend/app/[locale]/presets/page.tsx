'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { PresetTable } from '@/components/presets/PresetTable';
import { PresetForm } from '@/components/presets/PresetForm';
import { usePresets } from '@/hooks/use-presets';

export default function PresetsPage() {
  const t = useTranslations('presets');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const { data: presets, isLoading } = usePresets();

  return (
    <div className="container py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('title')}</h1>
          <p className="text-muted-foreground">{t('subtitle')}</p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          {t('create')}
        </Button>
      </div>

      <PresetTable presets={presets || []} isLoading={isLoading} />

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('createTitle')}</DialogTitle>
          </DialogHeader>
          <PresetForm
            onSuccess={() => {
              setCreateDialogOpen(false);
              toast.success(t('createSuccess'));
            }}
            onCancel={() => setCreateDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
