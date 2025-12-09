'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useFlavorStats } from '@/hooks/use-services';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { FlavorUsageChart } from './FlavorUsageChart';
import { formatTokenCount, formatCost, formatLatency } from '@/lib/format-number';

interface FlavorAnalyticsProps {
  flavorId: string;
  flavorName: string;
}

export function FlavorAnalytics({ flavorId, flavorName }: FlavorAnalyticsProps) {
  const t = useTranslations('flavors.analytics');
  const [period, setPeriod] = useState<'24h' | '7d' | '30d' | 'all'>('24h');
  const { data: stats, isLoading } = useFlavorStats(flavorId, period);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-full" />
        <div className="grid grid-cols-4 gap-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        {t('noData')}
      </div>
    );
  }

  const { stats: data } = stats;

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">
          {t('title')}: {flavorName}
        </h3>
        <Select value={period} onValueChange={(value: any) => setPeriod(value)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="24h">{t('period.24h')}</SelectItem>
            <SelectItem value="7d">{t('period.7d')}</SelectItem>
            <SelectItem value="30d">{t('period.30d')}</SelectItem>
            <SelectItem value="all">{t('period.all')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('totalRequests')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {data.total_requests.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('successRate')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {data.success_rate.toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {data.successful_requests} / {data.total_requests}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('avgLatency')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatLatency(data.avg_latency_ms)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('totalCost')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatCost(data.total_estimated_cost)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {formatCost(data.avg_cost_per_request)} {t('perRequest')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Usage Over Time Chart */}
      <Card>
        <CardHeader>
          <CardTitle>{t('usageOverTime')}</CardTitle>
        </CardHeader>
        <CardContent>
          <FlavorUsageChart data={data.time_series} period={period} />
        </CardContent>
      </Card>

      {/* Token Statistics */}
      <Card>
        <CardHeader>
          <CardTitle>{t('tokenStatistics')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">{t('totalTokens')}</p>
              <p className="text-2xl font-semibold">
                {formatTokenCount(data.total_tokens)}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">{t('inputTokens')}</p>
              <p className="text-2xl font-semibold">
                {formatTokenCount(data.total_input_tokens)}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">{t('outputTokens')}</p>
              <p className="text-2xl font-semibold">
                {formatTokenCount(data.total_output_tokens)}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">{t('avgInputTokens')}</p>
              <p className="text-2xl font-semibold">
                {formatTokenCount(Math.round(data.avg_input_tokens))}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">{t('avgOutputTokens')}</p>
              <p className="text-2xl font-semibold">
                {formatTokenCount(Math.round(data.avg_output_tokens))}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Latency Percentiles */}
      <Card>
        <CardHeader>
          <CardTitle>{t('latencyPercentiles')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">{t('minLatency')}</p>
              <p className="text-2xl font-semibold">{formatLatency(data.min_latency_ms)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">P50</p>
              <p className="text-2xl font-semibold">{formatLatency(data.p50_latency_ms)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">P95</p>
              <p className="text-2xl font-semibold">{formatLatency(data.p95_latency_ms)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">P99</p>
              <p className="text-2xl font-semibold">{formatLatency(data.p99_latency_ms)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{t('maxLatency')}</p>
              <p className="text-2xl font-semibold">{formatLatency(data.max_latency_ms)}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
