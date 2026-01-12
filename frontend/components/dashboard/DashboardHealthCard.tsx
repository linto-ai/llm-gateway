'use client';

import { useTranslations, useLocale } from 'next-intl';
import { useRouter } from '@/lib/navigation';
import { Activity, AlertTriangle, CheckCircle, Clock, XCircle, Zap } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useDashboardAnalytics } from '@/hooks/use-analytics';
import { formatTokenCount, formatCost, formatLatency } from '@/lib/format-number';
import type { HealthStatus } from '@/types/analytics';

/**
 * Status badge configuration
 */
const statusConfig: Record<HealthStatus, { variant: 'default' | 'secondary' | 'outline' | 'destructive'; icon: typeof CheckCircle }> = {
  healthy: { variant: 'default', icon: CheckCircle },
  degraded: { variant: 'secondary', icon: AlertTriangle },
  unhealthy: { variant: 'destructive', icon: XCircle },
  inactive: { variant: 'outline', icon: Clock },
};

/**
 * Get color class for success rate
 */
function getSuccessRateColor(rate: number): string {
  if (rate >= 95) return 'text-green-600 dark:text-green-400';
  if (rate >= 80) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

/**
 * DashboardHealthCard displays system-wide health overview for the last 24 hours.
 */
export function DashboardHealthCard() {
  const t = useTranslations('analytics.dashboard');
  const tStatus = useTranslations('analytics.status');
  const router = useRouter();
  const locale = useLocale();

  const { data: analytics, isLoading, error } = useDashboardAnalytics();

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            <Skeleton className="h-6 w-32" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !analytics) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            {t('title')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">{t('error')}</p>
        </CardContent>
      </Card>
    );
  }

  const { overview, services, recent_failures } = analytics;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            {t('title')}
          </CardTitle>
          <span className="text-sm text-muted-foreground">{t('subtitle')}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Total Jobs */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">{t('totalJobs')}</p>
            <p className="text-2xl font-bold">{overview.total_jobs.toLocaleString()}</p>
            <p className="text-xs text-muted-foreground">
              {overview.successful_jobs} / {overview.failed_jobs}
            </p>
          </div>

          {/* Success Rate */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">{t('successRate')}</p>
            <p className={`text-2xl font-bold ${getSuccessRateColor(overview.success_rate)}`}>
              {overview.success_rate.toFixed(1)}%
            </p>
          </div>

          {/* Total Tokens */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">{t('totalTokens')}</p>
            <p className="text-2xl font-bold">{formatTokenCount(overview.total_tokens)}</p>
          </div>

          {/* Total Cost */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">{t('totalCost')}</p>
            <p className="text-2xl font-bold">{formatCost(overview.total_cost)}</p>
          </div>
        </div>

        {/* Service Health */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium">{t('serviceHealth')}</h4>
            <span className="text-xs text-muted-foreground">
              {overview.active_services} {t('activeServices').toLowerCase()}
            </span>
          </div>
          {services.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t('noServices')}</p>
          ) : (
            <div className="space-y-2">
              {services.slice(0, 5).map((service) => {
                const config = statusConfig[service.status];
                const StatusIcon = config.icon;
                return (
                  <div
                    key={service.service_id}
                    className="flex items-center justify-between py-1.5 px-2 rounded-md hover:bg-muted/50 cursor-pointer transition-colors"
                    onClick={() => router.push(`/services/${service.service_id}`)}
                  >
                    <div className="flex items-center gap-2">
                      <StatusIcon className={`h-4 w-4 ${
                        service.status === 'healthy' ? 'text-green-500' :
                        service.status === 'degraded' ? 'text-yellow-500' :
                        service.status === 'unhealthy' ? 'text-red-500' :
                        'text-muted-foreground'
                      }`} />
                      <span className="text-sm font-medium">{service.service_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        {service.success_rate.toFixed(1)}%
                      </span>
                      <Badge variant={config.variant} className="text-xs">
                        {tStatus(service.status)}
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Failures */}
        <div>
          <h4 className="text-sm font-medium mb-2">{t('recentFailures')}</h4>
          {recent_failures.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckCircle className="h-4 w-4 text-green-500" />
              {t('noFailures')}
            </div>
          ) : (
            <div className="space-y-2">
              {recent_failures.slice(0, 5).map((failure) => (
                <div
                  key={failure.job_id}
                  className="flex items-start justify-between py-1.5 px-2 rounded-md bg-red-50 dark:bg-red-950/20"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                      <span className="text-sm font-medium truncate">
                        {failure.service_name}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground ml-6 truncate">
                      {failure.error}
                    </p>
                  </div>
                  <span className="text-xs text-muted-foreground flex-shrink-0 ml-2">
                    {formatDistanceToNow(new Date(failure.timestamp), { addSuffix: true })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
