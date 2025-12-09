'use client';

import { useTranslations } from 'next-intl';
import { format, formatDistanceToNow } from 'date-fns';
import { enUS, fr } from 'date-fns/locale';
import { CheckCircle, AlertCircle, XCircle, HelpCircle, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { ModelResponse, HealthStatus } from '@/types/model';

interface ModelHealthStatusProps {
  model: ModelResponse;
  onVerify: () => void;
  verifying: boolean;
  locale?: string;
}

const healthStatusConfig: Record<
  HealthStatus,
  { icon: React.ElementType; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  available: { icon: CheckCircle, variant: 'default' },
  unavailable: { icon: AlertCircle, variant: 'secondary' },
  error: { icon: XCircle, variant: 'destructive' },
  unknown: { icon: HelpCircle, variant: 'outline' },
};

export function ModelHealthStatus({ model, onVerify, verifying, locale = 'en' }: ModelHealthStatusProps) {
  const t = useTranslations('models');
  const dateLocale = locale === 'fr' ? fr : enUS;

  const config = healthStatusConfig[model.health_status];
  const Icon = config.icon;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge variant={config.variant} className="flex items-center gap-1">
            <Icon className="h-3 w-3" />
            {t(`health.${model.health_status}`)}
          </Badge>
          {model.health_checked_at && (
            <span className="text-sm text-muted-foreground">
              {t('health.lastChecked')}: {formatDistanceToNow(new Date(model.health_checked_at), {
                addSuffix: true,
                locale: dateLocale
              })}
            </span>
          )}
          {!model.health_checked_at && (
            <span className="text-sm text-muted-foreground">{t('health.neverChecked')}</span>
          )}
        </div>
        <Button
          onClick={onVerify}
          disabled={verifying}
          size="sm"
          variant="outline"
        >
          {verifying ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('health.verifying')}
            </>
          ) : (
            t('health.verifyNow')
          )}
        </Button>
      </div>

      {model.health_error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{model.health_error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
