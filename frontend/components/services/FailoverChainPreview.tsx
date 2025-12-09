'use client';

import { useTranslations } from 'next-intl';
import { useFailoverChain } from '@/hooks/use-failover-chain';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, AlertTriangle, Loader2 } from 'lucide-react';
import { Fragment } from 'react';

interface FailoverChainPreviewProps {
  serviceId: string;
  flavorId?: string;
}

export function FailoverChainPreview({ serviceId, flavorId }: FailoverChainPreviewProps) {
  const t = useTranslations('services.flavors.failoverConfig');
  const { data: chainData, isLoading, error } = useFailoverChain(serviceId, flavorId);

  if (!flavorId) return null;

  if (isLoading) {
    return (
      <div className="mt-2 p-3 bg-muted rounded-lg">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('loading')}
        </div>
      </div>
    );
  }

  if (error) {
    return null;
  }

  const chain = chainData?.chain || [];

  if (chain.length <= 1) {
    return (
      <div className="mt-2 text-sm text-muted-foreground">
        {t('noChain')}
      </div>
    );
  }

  const hasInactiveFlavorInChain = chain.some(f => !f.is_active);

  return (
    <div className="mt-2 p-3 bg-muted rounded-lg">
      <div className="text-xs font-medium text-muted-foreground mb-2">
        {t('chainPreview')}
      </div>
      <div className="flex flex-wrap items-center gap-1">
        {chain.map((flavor, index) => (
          <Fragment key={flavor.id}>
            {index > 0 && <ArrowRight className="h-3 w-3 text-muted-foreground mx-1" />}
            <Badge
              variant={index === 0 ? 'default' : 'secondary'}
              className={!flavor.is_active ? 'opacity-50' : ''}
            >
              {flavor.name}
              {!flavor.is_active && (
                <AlertTriangle className="h-3 w-3 ml-1 text-yellow-500" />
              )}
            </Badge>
          </Fragment>
        ))}
      </div>
      {hasInactiveFlavorInChain && (
        <div className="text-xs text-yellow-600 mt-2 flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" />
          {t('inactiveWarning')}
        </div>
      )}
    </div>
  );
}
