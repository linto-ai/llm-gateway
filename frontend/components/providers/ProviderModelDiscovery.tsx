'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useDiscoverProviderModels } from '@/hooks/use-models';
import type { DiscoveredModel } from '@/types/model';

interface ProviderModelDiscoveryProps {
  providerId: string;
  onImport: (models: DiscoveredModel[]) => Promise<void>;
}

export function ProviderModelDiscovery({ providerId, onImport }: ProviderModelDiscoveryProps) {
  const t = useTranslations('providers');
  const tModels = useTranslations('models.fields');
  const tCommon = useTranslations('common');
  const [open, setOpen] = useState(false);
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);

  const discoverMutation = useDiscoverProviderModels();

  const handleDiscover = () => {
    setOpen(true);
    setSelectedModels(new Set());
    discoverMutation.mutate(providerId, {
      onError: () => {
        toast.error(t('discovery.discoveryFailed'));
      },
    });
  };

  const toggleModel = (modelIdentifier: string) => {
    setSelectedModels((prev) => {
      const next = new Set(prev);
      if (next.has(modelIdentifier)) {
        next.delete(modelIdentifier);
      } else {
        next.add(modelIdentifier);
      }
      return next;
    });
  };

  const handleImport = async () => {
    if (!discoverMutation.data || selectedModels.size === 0) return;

    const modelsToImport = discoverMutation.data.filter((m) =>
      selectedModels.has(m.model_identifier)
    );

    setImporting(true);
    try {
      await onImport(modelsToImport);
      setOpen(false);
      setSelectedModels(new Set());
    } catch (error: unknown) {
      // Handle 409 Conflict (model already exists)
      if (error instanceof Error && 'status' in error && (error as { status: number }).status === 409) {
        toast.warning(t('discovery.importConflict'));
      } else {
        toast.error(t('discovery.importError'));
      }
    } finally {
      setImporting(false);
    }
  };

  const discoveredModels = discoverMutation.data || [];
  const selectedCount = selectedModels.size;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button onClick={handleDiscover}>
          {t('discovery.discoverModels')}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('discovery.discoveredModels')}</DialogTitle>
          <DialogDescription>{t('discovery.selectModels')}</DialogDescription>
        </DialogHeader>

        {discoverMutation.isPending && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="ml-2">{t('discovery.discovering')}</span>
          </div>
        )}

        {discoverMutation.isSuccess && discoveredModels.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            {t('discovery.noModelsFound')}
          </div>
        )}

        {discoverMutation.isSuccess && discoveredModels.length > 0 && (
          <div className="space-y-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12"></TableHead>
                  <TableHead>{tModels('name')}</TableHead>
                  <TableHead>{tModels('contextLength')}</TableHead>
                  <TableHead>{tModels('maxGenerationLength')}</TableHead>
                  <TableHead>{tModels('tokenizer')}</TableHead>
                  <TableHead>{tCommon('status')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {discoveredModels.map((model) => (
                  <TableRow key={model.model_identifier}>
                    <TableCell>
                      <Checkbox
                        checked={selectedModels.has(model.model_identifier)}
                        onCheckedChange={() => toggleModel(model.model_identifier)}
                      />
                    </TableCell>
                    <TableCell className="font-medium">{model.model_name}</TableCell>
                    <TableCell>{model.context_length.toLocaleString()}</TableCell>
                    <TableCell>{model.max_generation_length.toLocaleString()}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {model.tokenizer_name || model.tokenizer_class || '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={model.available ? 'default' : 'secondary'}>
                        {model.available ? tCommon('available') : tCommon('unavailable')}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOpen(false)}>
                {tCommon('cancel')}
              </Button>
              <Button
                onClick={handleImport}
                disabled={selectedCount === 0 || importing}
              >
                {importing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('discovery.importing')}
                  </>
                ) : (
                  t('discovery.importSelected', { count: selectedCount })
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
