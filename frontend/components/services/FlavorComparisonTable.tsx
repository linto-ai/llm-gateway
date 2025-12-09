'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { ArrowUpDown } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { useServiceFlavorComparison } from '@/hooks/use-services';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface FlavorComparisonTableProps {
  serviceId: string;
}

type SortField = 'requests' | 'success_rate' | 'latency' | 'cost' | 'usage_percentage';

export function FlavorComparisonTable({ serviceId }: FlavorComparisonTableProps) {
  const t = useTranslations('flavors.analytics');
  const tCommon = useTranslations('common');
  const [period, setPeriod] = useState<'24h' | '7d' | '30d' | 'all'>('24h');
  const [sortField, setSortField] = useState<SortField>('requests');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const { data: comparison, isLoading } = useServiceFlavorComparison(serviceId, period);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedFlavors = comparison?.flavors
    ? [...comparison.flavors].sort((a, b) => {
        let aValue: number;
        let bValue: number;

        switch (sortField) {
          case 'requests':
            aValue = a.total_requests;
            bValue = b.total_requests;
            break;
          case 'success_rate':
            aValue = a.success_rate;
            bValue = b.success_rate;
            break;
          case 'latency':
            aValue = a.avg_latency_ms;
            bValue = b.avg_latency_ms;
            break;
          case 'cost':
            aValue = a.total_estimated_cost;
            bValue = b.total_estimated_cost;
            break;
          case 'usage_percentage':
            aValue = a.usage_percentage;
            bValue = b.usage_percentage;
            break;
          default:
            return 0;
        }

        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      })
    : [];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!comparison || comparison.flavors.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        {t('noData')}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Period Selector */}
      <div className="flex justify-end">
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

      {/* Comparison Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('flavorName')}</TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort('requests')}
                  className="h-8 px-2"
                >
                  {t('totalRequests')}
                  <ArrowUpDown className="ml-2 h-3 w-3" />
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort('success_rate')}
                  className="h-8 px-2"
                >
                  {t('successRate')}
                  <ArrowUpDown className="ml-2 h-3 w-3" />
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort('latency')}
                  className="h-8 px-2"
                >
                  {t('avgLatency')}
                  <ArrowUpDown className="ml-2 h-3 w-3" />
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort('cost')}
                  className="h-8 px-2"
                >
                  {t('totalCost')}
                  <ArrowUpDown className="ml-2 h-3 w-3" />
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort('usage_percentage')}
                  className="h-8 px-2"
                >
                  {t('usagePercentage')}
                  <ArrowUpDown className="ml-2 h-3 w-3" />
                </Button>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedFlavors.map((flavor) => (
              <TableRow
                key={flavor.flavor_id}
                className={flavor.is_default ? 'bg-accent/50' : ''}
              >
                <TableCell>
                  <div className="flex items-center gap-2">
                    {flavor.flavor_name}
                    {flavor.is_default && (
                      <Badge variant="secondary" className="text-xs">
                        {tCommon('default')}
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell>{flavor.total_requests.toLocaleString()}</TableCell>
                <TableCell>{flavor.success_rate.toFixed(1)}%</TableCell>
                <TableCell>{flavor.avg_latency_ms.toFixed(0)}ms</TableCell>
                <TableCell>${flavor.total_estimated_cost.toFixed(2)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <Progress value={flavor.usage_percentage} className="w-20" />
                    <span className="text-sm text-muted-foreground min-w-[3rem]">
                      {flavor.usage_percentage.toFixed(1)}%
                    </span>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Totals Summary */}
      <div className="grid grid-cols-3 gap-4 pt-4 border-t">
        <div className="text-center">
          <p className="text-sm text-muted-foreground">{t('totalRequests')}</p>
          <p className="text-2xl font-semibold">
            {comparison.totals.total_requests.toLocaleString()}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-muted-foreground">{t('totalTokens')}</p>
          <p className="text-2xl font-semibold">
            {comparison.totals.total_tokens.toLocaleString()}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-muted-foreground">{t('totalCost')}</p>
          <p className="text-2xl font-semibold">
            ${comparison.totals.total_cost.toFixed(2)}
          </p>
        </div>
      </div>
    </div>
  );
}
