'use client';

import { useTranslations, useLocale } from 'next-intl';
import { Zap, RefreshCw } from 'lucide-react';

import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { usePresets } from '@/hooks/use-presets';
import { useServiceTypeConfig } from '@/hooks/use-service-types';
import type { FlavorPreset, FlavorPresetConfig } from '@/types/preset';
import type { ProcessingMode } from '@/types/service';

interface FlavorPresetSelectorProps {
  serviceType?: string;
  onSelect: (config: FlavorPresetConfig) => void;
}

const modeIcons: Record<ProcessingMode, typeof Zap> = {
  single_pass: Zap,
  iterative: RefreshCw,
};

export function FlavorPresetSelector({
  serviceType = 'summary',
  onSelect,
}: FlavorPresetSelectorProps) {
  const t = useTranslations('presets');
  const tServices = useTranslations('services.flavors');
  const locale = useLocale();

  // Fetch service type config to check capabilities
  const { data: serviceTypeConfig } = useServiceTypeConfig(serviceType);
  const { data: presets, isLoading } = usePresets(serviceType);

  // Show message if service type doesn't support presets (no reduce and no chunking)
  if (serviceTypeConfig && !serviceTypeConfig.supports_reduce && !serviceTypeConfig.supports_chunking) {
    return (
      <p className="text-sm text-muted-foreground italic">
        {tServices('presetsNotApplicable')}
      </p>
    );
  }

  // Filter presets based on service type capabilities
  const filteredPresets = presets?.filter((preset: FlavorPreset) => {
    // If service doesn't support chunking, filter out iterative presets
    if (!serviceTypeConfig?.supports_chunking && preset.config.processing_mode === 'iterative') {
      return false;
    }
    return true;
  }) || [];

  if (isLoading || filteredPresets.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <Label>{t('startFromPreset')}</Label>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {filteredPresets.map((preset: FlavorPreset) => {
          const Icon = modeIcons[preset.config.processing_mode] || RefreshCw;
          const description = locale === 'fr' ? preset.description_fr : preset.description_en;

          return (
            <Card
              key={preset.id}
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => onSelect(preset.config)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">{preset.name}</CardTitle>
                  {preset.is_system && (
                    <Badge variant="secondary" className="text-xs">
                      {t('system')}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground line-clamp-2">
                  {description}
                </p>
                <Badge variant="outline" className="mt-2 text-xs gap-1">
                  <Icon className="h-3 w-3" />
                  {preset.config.processing_mode.replace('_', ' ')}
                </Badge>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
