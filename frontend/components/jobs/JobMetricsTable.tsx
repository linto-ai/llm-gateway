'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { ChevronDown, ChevronRight, TableIcon } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import type { JobTokenMetrics, PassType } from '@/types/job';

interface JobMetricsTableProps {
  metrics: JobTokenMetrics;
}

// Format duration from milliseconds
function formatDuration(ms: number): string {
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
}

// Format token count with thousands separator
function formatTokens(count: number): string {
  return count.toLocaleString();
}

// Format cost in USD with 4 decimal places
function formatCost(cost: number | null): string {
  if (cost === null) return '-';
  return `$${cost.toFixed(4)}`;
}

// Pass type badge variants
const passTypeVariants: Record<PassType, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  initial: 'default',
  continuation: 'secondary',
  reduce: 'outline',
  summary: 'default',
  single_pass: 'default',
  extraction: 'secondary',
  categorization: 'secondary',
};

export function JobMetricsTable({ metrics }: JobMetricsTableProps) {
  const t = useTranslations('jobs');
  const [isOpen, setIsOpen] = useState(false);

  if (!metrics || metrics.passes.length === 0) {
    return null;
  }

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-2">
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="w-full justify-between p-0 h-auto hover:bg-transparent">
              <CardTitle className="text-lg flex items-center gap-2">
                <TableIcon className="h-5 w-5" />
                {t('metrics.breakdown')}
              </CardTitle>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>
                  {isOpen ? t('metrics.hideDetails') : t('metrics.showDetails')}
                </span>
                {isOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </div>
            </Button>
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="pt-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">{t('metrics.pass', { number: '' }).replace('{number}', '#')}</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">{t('metrics.duration')}</TableHead>
                  <TableHead className="text-right">{t('metrics.promptTokens')}</TableHead>
                  <TableHead className="text-right">{t('metrics.completionTokens')}</TableHead>
                  <TableHead className="text-right">{t('metrics.totalTokens')}</TableHead>
                  <TableHead className="text-right">{t('metrics.estimatedCost')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {metrics.passes.map((pass) => (
                  <TableRow key={pass.pass_number}>
                    <TableCell className="font-medium">{pass.pass_number}</TableCell>
                    <TableCell>
                      <Badge variant={passTypeVariants[pass.pass_type]} className="text-xs">
                        {t(`metrics.passType.${pass.pass_type}`)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {formatDuration(pass.duration_ms)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm text-blue-600">
                      {formatTokens(pass.prompt_tokens)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm text-green-600">
                      {formatTokens(pass.completion_tokens)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {formatTokens(pass.total_tokens)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm text-amber-600">
                      {formatCost(pass.estimated_cost)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
              <TableFooter>
                <TableRow className="font-semibold">
                  <TableCell>Total</TableCell>
                  <TableCell>
                    <span className="text-xs text-muted-foreground">
                      {t('metrics.totalPasses', { count: metrics.passes.length })}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatDuration(metrics.total_duration_ms)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-blue-600">
                    {formatTokens(metrics.total_prompt_tokens)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-green-600">
                    {formatTokens(metrics.total_completion_tokens)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatTokens(metrics.total_tokens)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-amber-600">
                    {formatCost(metrics.total_estimated_cost)}
                  </TableCell>
                </TableRow>
              </TableFooter>
            </Table>

            {/* Averages summary */}
            <div className="flex items-center justify-end gap-6 mt-4 text-sm text-muted-foreground">
              <span>
                {t('metrics.avgPerPass')}: {formatTokens(Math.round(metrics.avg_tokens_per_pass))} tokens
              </span>
              <span>
                {t('metrics.avgPerPass')}: {formatDuration(metrics.avg_duration_per_pass_ms)}
              </span>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
