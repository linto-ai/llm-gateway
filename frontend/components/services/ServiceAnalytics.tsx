'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
} from 'recharts';
import { format } from 'date-fns';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { useServiceStats } from '@/hooks/use-analytics';
import { formatTokenCount, formatCost, formatLatency } from '@/lib/format-number';
import type { AnalyticsPeriod } from '@/types/analytics';

interface ServiceAnalyticsProps {
  serviceId: string;
  serviceName: string;
}

// Colors for pie chart
const COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
];

/**
 * Get color class for success rate
 */
function getSuccessRateColor(rate: number): string {
  if (rate >= 95) return 'text-green-600 dark:text-green-400';
  if (rate >= 80) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

export function ServiceAnalytics({ serviceId, serviceName }: ServiceAnalyticsProps) {
  const t = useTranslations('analytics.service');
  const tPeriods = useTranslations('analytics.periods');
  const tChart = useTranslations('analytics.chart');

  const [period, setPeriod] = useState<AnalyticsPeriod>('24h');
  const { data: stats, isLoading, error } = useServiceStats(serviceId, period);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-[180px]" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        {t('noData')}
      </div>
    );
  }

  const { stats: data, flavor_breakdown, time_series } = stats;

  // Format timestamp based on period
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    if (period === '24h') {
      return format(date, 'HH:mm');
    }
    return format(date, 'MMM dd');
  };

  // Transform time series data for chart
  const chartData = time_series.map((point) => ({
    ...point,
    formattedTimestamp: formatTimestamp(point.timestamp),
  }));

  return (
    <div className="space-y-6">
      {/* Header with Period Selector */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">
          {t('title')}: {serviceName}
        </h3>
        <Select value={period} onValueChange={(value) => setPeriod(value as AnalyticsPeriod)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="24h">{tPeriods('24h')}</SelectItem>
            <SelectItem value="7d">{tPeriods('7d')}</SelectItem>
            <SelectItem value="30d">{tPeriods('30d')}</SelectItem>
            <SelectItem value="all">{tPeriods('all')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
            <p className="text-xs text-muted-foreground mt-1">
              {data.successful_requests} / {data.failed_requests}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('successRate')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getSuccessRateColor(data.success_rate)}`}>
              {data.success_rate.toFixed(1)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('totalTokens')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatTokenCount(data.total_tokens)}
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
          </CardContent>
        </Card>
      </div>

      {/* Additional Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('avgLatency')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatLatency(data.avg_latency_ms)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('flavorsUsed')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {data.flavors_used}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('mostUsedFlavor')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold truncate">
              {data.most_used_flavor || '-'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Flavor Breakdown */}
      {flavor_breakdown.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('flavorBreakdown')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col md:flex-row gap-6">
              {/* Pie Chart */}
              <div className="flex-1 h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={flavor_breakdown}
                      dataKey="requests"
                      nameKey="flavor_name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, percentage }) => `${name} (${percentage.toFixed(1)}%)`}
                      labelLine={false}
                    >
                      {flavor_breakdown.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '6px',
                      }}
                      formatter={(value: number, name: string) => [
                        `${value.toLocaleString()} requests`,
                        name,
                      ]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Flavor List */}
              <div className="flex-1 space-y-2">
                {flavor_breakdown.map((flavor, index) => (
                  <div
                    key={flavor.flavor_id}
                    className="flex items-center justify-between py-2 px-3 rounded-md hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <span className="font-medium">{flavor.flavor_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        {flavor.requests.toLocaleString()}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {flavor.percentage.toFixed(1)}%
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Usage Over Time Chart */}
      {time_series.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('usageOverTime')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="formattedTimestamp"
                    className="text-xs"
                    stroke="currentColor"
                  />
                  <YAxis
                    yAxisId="left"
                    className="text-xs"
                    stroke="currentColor"
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    className="text-xs"
                    stroke="currentColor"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                    formatter={(value: number, name: string) => {
                      if (name === 'cost') return [formatCost(value), tChart('cost')];
                      if (name === 'tokens') return [formatTokenCount(value), tChart('tokens')];
                      return [value.toLocaleString(), tChart('requests')];
                    }}
                  />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="requests"
                    stroke="hsl(var(--primary))"
                    name={tChart('requests')}
                    strokeWidth={2}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="cost"
                    stroke="hsl(var(--chart-2))"
                    name={tChart('cost')}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
