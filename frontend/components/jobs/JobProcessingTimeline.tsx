'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Clock, Timer, ChevronDown, ChevronRight, Zap, Repeat, FileSearch, Tag } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { formatTokenCount, formatLatency } from '@/lib/format-number';
import type { JobPassMetrics, JobTokenMetrics, PassType } from '@/types/job';

interface JobProcessingTimelineProps {
  metrics: JobTokenMetrics | null;
  processingMode: 'single_pass' | 'iterative';
  currentPassNumber?: number;
  isLive?: boolean;
}

// Pass type badge variants and icons
const passTypeConfig: Record<PassType, {
  variant: 'default' | 'secondary' | 'outline' | 'destructive';
  icon: React.ReactNode;
  color: string;
}> = {
  initial: { variant: 'default', icon: null, color: 'bg-blue-500' },
  continuation: { variant: 'secondary', icon: null, color: 'bg-blue-400' },
  single_pass: { variant: 'default', icon: <Zap className="h-3 w-3" />, color: 'bg-purple-500' },
  reduce: { variant: 'outline', icon: <Repeat className="h-3 w-3" />, color: 'bg-orange-500' },
  summary: { variant: 'default', icon: null, color: 'bg-green-500' },
  extraction: { variant: 'secondary', icon: <FileSearch className="h-3 w-3" />, color: 'bg-teal-500' },
  categorization: { variant: 'secondary', icon: <Tag className="h-3 w-3" />, color: 'bg-pink-500' },
};

// Format cost in USD
function formatCost(cost: number | null): string {
  if (cost === null) return '-';
  return `$${cost.toFixed(4)}`;
}

export function JobProcessingTimeline({
  metrics,
  processingMode,
  currentPassNumber,
  isLive = false,
}: JobProcessingTimelineProps) {
  const t = useTranslations('jobs');
  const [showDetails, setShowDetails] = useState(false);

  const passes = metrics?.passes || [];

  // Calculate the max duration for relative bar sizing
  const maxDuration = useMemo(() => {
    if (passes.length === 0) return 1;
    return Math.max(...passes.map((p) => p.duration_ms), 1);
  }, [passes]);

  // Group passes by category for summary
  const passSummary = useMemo(() => {
    const summary = {
      processing: { count: 0, tokens: 0, duration: 0 },
      reduce: { count: 0, tokens: 0, duration: 0 },
      extraction: { count: 0, tokens: 0, duration: 0 },
      categorization: { count: 0, tokens: 0, duration: 0 },
    };

    for (const pass of passes) {
      if (pass.pass_type === 'initial' || pass.pass_type === 'continuation' || pass.pass_type === 'single_pass') {
        summary.processing.count++;
        summary.processing.tokens += pass.total_tokens;
        summary.processing.duration += pass.duration_ms;
      } else if (pass.pass_type === 'reduce' || pass.pass_type === 'summary') {
        summary.reduce.count++;
        summary.reduce.tokens += pass.total_tokens;
        summary.reduce.duration += pass.duration_ms;
      } else if (pass.pass_type === 'extraction') {
        summary.extraction.count++;
        summary.extraction.tokens += pass.total_tokens;
        summary.extraction.duration += pass.duration_ms;
      } else if (pass.pass_type === 'categorization') {
        summary.categorization.count++;
        summary.categorization.tokens += pass.total_tokens;
        summary.categorization.duration += pass.duration_ms;
      }
    }

    return summary;
  }, [passes]);

  // If no metrics at all, show minimal info
  if (!metrics || passes.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Timer className="h-5 w-5" />
              {t('metrics.timeline')}
            </CardTitle>
            <Badge variant={processingMode === 'single_pass' ? 'default' : 'secondary'}>
              {processingMode === 'single_pass' ? (
                <><Zap className="h-3 w-3 mr-1" />{t('processingMode.singlePass')}</>
              ) : (
                <><Repeat className="h-3 w-3 mr-1" />{t('processingMode.iterative')}</>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t('metrics.noData')}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Timer className="h-5 w-5" />
            {t('metrics.timeline')}
          </CardTitle>
          <Badge variant={processingMode === 'single_pass' ? 'default' : 'secondary'}>
            {processingMode === 'single_pass' ? (
              <><Zap className="h-3 w-3 mr-1" />{t('processingMode.singlePass')}</>
            ) : (
              <><Repeat className="h-3 w-3 mr-1" />{t('processingMode.iterative')}</>
            )}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary badges for each phase */}
        <div className="flex flex-wrap gap-2">
          {passSummary.processing.count > 0 && (
            <Badge variant="outline" className="gap-1">
              <div className="w-2 h-2 rounded-full bg-blue-500" />
              {t('metrics.phases.processing')}: {passSummary.processing.count} {t('metrics.passes', { count: passSummary.processing.count })}
              <span className="text-muted-foreground">({formatTokenCount(passSummary.processing.tokens)} tokens)</span>
            </Badge>
          )}
          {passSummary.reduce.count > 0 && (
            <Badge variant="outline" className="gap-1">
              <div className="w-2 h-2 rounded-full bg-orange-500" />
              {t('metrics.phases.reduce')}: {passSummary.reduce.count}
              <span className="text-muted-foreground">({formatTokenCount(passSummary.reduce.tokens)} tokens)</span>
            </Badge>
          )}
          {passSummary.extraction.count > 0 && (
            <Badge variant="outline" className="gap-1">
              <div className="w-2 h-2 rounded-full bg-teal-500" />
              {t('metrics.phases.extraction')}: {passSummary.extraction.count}
              <span className="text-muted-foreground">({formatTokenCount(passSummary.extraction.tokens)} tokens)</span>
            </Badge>
          )}
          {passSummary.categorization.count > 0 && (
            <Badge variant="outline" className="gap-1">
              <div className="w-2 h-2 rounded-full bg-pink-500" />
              {t('metrics.phases.categorization')}: {passSummary.categorization.count}
              <span className="text-muted-foreground">({formatTokenCount(passSummary.categorization.tokens)} tokens)</span>
            </Badge>
          )}
        </div>

        {/* Visual timeline entries */}
        <div className="space-y-3">
          {passes.map((pass) => {
            const isCurrentPass = isLive && pass.pass_number === currentPassNumber;
            const durationPercent = Math.max((pass.duration_ms / maxDuration) * 100, 5);
            const config = passTypeConfig[pass.pass_type] || passTypeConfig.initial;

            return (
              <div
                key={pass.pass_number}
                className={`space-y-1.5 ${isCurrentPass ? 'bg-primary/5 -mx-2 px-2 py-2 rounded-md' : ''}`}
              >
                {/* Pass header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">
                      {t('metrics.pass', { number: pass.pass_number })}
                    </span>
                    <Badge variant={config.variant} className="text-xs gap-1">
                      {config.icon}
                      {t(`metrics.passType.${pass.pass_type}`)}
                    </Badge>
                    {isCurrentPass && (
                      <Badge variant="outline" className="text-xs animate-pulse">
                        <Clock className="h-3 w-3 mr-1" />
                        {t('metrics.liveUpdates')}
                      </Badge>
                    )}
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {formatLatency(pass.duration_ms)}
                  </span>
                </div>

                {/* Duration bar with color coding */}
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      isCurrentPass ? 'animate-pulse' : ''
                    } ${config.color}`}
                    style={{ width: `${durationPercent}%` }}
                  />
                </div>

                {/* Token breakdown */}
                <div className="text-xs text-muted-foreground pl-4">
                  {formatTokenCount(pass.total_tokens)} tokens (
                  <span className="text-blue-500">{formatTokenCount(pass.prompt_tokens)} prompt</span>
                  {' + '}
                  <span className="text-green-500">{formatTokenCount(pass.completion_tokens)} completion</span>
                  )
                  {pass.estimated_cost !== null && (
                    <span className="ml-2 text-amber-600">{formatCost(pass.estimated_cost)}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Totals summary */}
        <div className="flex items-center justify-between pt-3 border-t text-sm">
          <span className="text-muted-foreground">
            {t('metrics.totalPasses', { count: passes.length })}
          </span>
          <div className="flex items-center gap-4">
            <span>
              <span className="text-muted-foreground">{t('metrics.duration')}: </span>
              <span className="font-medium">{formatLatency(metrics.total_duration_ms)}</span>
            </span>
            <span>
              <span className="text-muted-foreground">{t('metrics.totalTokens')}: </span>
              <span className="font-medium">{formatTokenCount(metrics.total_tokens)}</span>
            </span>
            {metrics.total_estimated_cost !== null && (
              <span>
                <span className="text-muted-foreground">{t('metrics.estimatedCost')}: </span>
                <span className="font-medium text-amber-600">{formatCost(metrics.total_estimated_cost)}</span>
              </span>
            )}
          </div>
        </div>

        {/* Collapsible detailed table */}
        <Collapsible open={showDetails} onOpenChange={setShowDetails}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="w-full justify-between">
              <span>{t('metrics.breakdown')}</span>
              {showDetails ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-2">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">{t('metrics.duration')}</TableHead>
                  <TableHead className="text-right">{t('metrics.promptTokens')}</TableHead>
                  <TableHead className="text-right">{t('metrics.completionTokens')}</TableHead>
                  <TableHead className="text-right">{t('metrics.totalTokens')}</TableHead>
                  <TableHead className="text-right">{t('metrics.estimatedCost')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {passes.map((pass) => {
                  const config = passTypeConfig[pass.pass_type] || passTypeConfig.initial;
                  return (
                    <TableRow key={pass.pass_number}>
                      <TableCell className="font-medium">{pass.pass_number}</TableCell>
                      <TableCell>
                        <Badge variant={config.variant} className="text-xs gap-1">
                          {config.icon}
                          {t(`metrics.passType.${pass.pass_type}`)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatLatency(pass.duration_ms)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-blue-600">
                        {formatTokenCount(pass.prompt_tokens)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-green-600">
                        {formatTokenCount(pass.completion_tokens)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatTokenCount(pass.total_tokens)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-amber-600">
                        {formatCost(pass.estimated_cost)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
              <TableFooter>
                <TableRow className="font-semibold">
                  <TableCell colSpan={2}>Total</TableCell>
                  <TableCell className="text-right font-mono">
                    {formatLatency(metrics.total_duration_ms)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-blue-600">
                    {formatTokenCount(metrics.total_prompt_tokens)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-green-600">
                    {formatTokenCount(metrics.total_completion_tokens)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatTokenCount(metrics.total_tokens)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-amber-600">
                    {formatCost(metrics.total_estimated_cost)}
                  </TableCell>
                </TableRow>
              </TableFooter>
            </Table>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}
