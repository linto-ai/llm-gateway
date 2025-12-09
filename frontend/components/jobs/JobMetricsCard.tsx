'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { Coins, MessageSquare, MessageSquareText, Activity } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatTokenCount, formatCost as formatCostUtil, formatLatency } from '@/lib/format-number';
import type { JobTokenMetrics, CumulativeMetrics } from '@/types/job';

interface JobMetricsCardProps {
  metrics: JobTokenMetrics | CumulativeMetrics | null;
  isLive?: boolean;
}

// Type guard to check if metrics is JobTokenMetrics (has passes array)
function isJobTokenMetrics(
  metrics: JobTokenMetrics | CumulativeMetrics
): metrics is JobTokenMetrics {
  return 'passes' in metrics;
}

// Format cost in USD with null handling
function formatCost(cost: number | null): string {
  if (cost === null) return '-';
  return formatCostUtil(cost);
}

export function JobMetricsCard({ metrics, isLive = false }: JobMetricsCardProps) {
  const t = useTranslations('jobs');

  // Calculate percentages for the visual bars
  const { promptPercent, completionPercent } = useMemo(() => {
    if (!metrics || metrics.total_tokens === 0) {
      return { promptPercent: 0, completionPercent: 0 };
    }
    const promptPct = Math.round((metrics.total_prompt_tokens / metrics.total_tokens) * 100);
    const completionPct = 100 - promptPct;
    return { promptPercent: promptPct, completionPercent: completionPct };
  }, [metrics]);

  // Get total duration - handle both metric types
  const totalDurationMs = useMemo(() => {
    if (!metrics) return 0;
    return metrics.total_duration_ms;
  }, [metrics]);

  // Get total estimated cost - handle both metric types
  const totalCost = useMemo(() => {
    if (!metrics) return null;
    return metrics.total_estimated_cost;
  }, [metrics]);

  if (!metrics) {
    return null;
  }

  return (
    <Card className={isLive ? 'ring-2 ring-primary/20' : ''}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Coins className="h-5 w-5" />
            {t('metrics.title')}
          </CardTitle>
          {isLive && (
            <Badge variant="outline" className="animate-pulse">
              <Activity className="h-3 w-3 mr-1" />
              {t('metrics.liveUpdates')}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Total Tokens */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{t('metrics.totalTokens')}</span>
            <span className="text-2xl font-bold">{formatTokenCount(metrics.total_tokens)}</span>
          </div>

          {/* Token Ratio Display */}
          <div className="text-xs text-muted-foreground text-right">
            {t('metrics.tokenRatio', {
              prompt: promptPercent,
              completion: completionPercent,
            })}
          </div>
        </div>

        {/* Prompt Tokens Bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-blue-500" />
              <span>{t('metrics.promptTokens')}</span>
            </div>
            <span className="font-medium">{formatTokenCount(metrics.total_prompt_tokens)}</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-500"
              style={{ width: `${promptPercent}%` }}
            />
          </div>
        </div>

        {/* Completion Tokens Bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <MessageSquareText className="h-4 w-4 text-green-500" />
              <span>{t('metrics.completionTokens')}</span>
            </div>
            <span className="font-medium">{formatTokenCount(metrics.total_completion_tokens)}</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all duration-500"
              style={{ width: `${completionPercent}%` }}
            />
          </div>
        </div>

        {/* Duration and Cost Row */}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="text-sm">
            <span className="text-muted-foreground">{t('metrics.duration')}: </span>
            <span className="font-medium">{formatLatency(totalDurationMs)}</span>
          </div>
          <div className="text-sm">
            <span className="text-muted-foreground">{t('metrics.estimatedCost')}: </span>
            <span className="font-medium text-amber-600">
              {totalCost !== null ? formatCost(totalCost) : t('metrics.noCost')}
            </span>
          </div>
        </div>

        {/* Average per pass (only for JobTokenMetrics with passes) */}
        {isJobTokenMetrics(metrics) && metrics.passes.length > 0 && (
          <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
            <span>
              {t('metrics.totalPasses', { count: metrics.passes.length })}
            </span>
            <span>
              {t('metrics.avgPerPass')}: {formatTokenCount(Math.round(metrics.avg_tokens_per_pass))} tokens
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
