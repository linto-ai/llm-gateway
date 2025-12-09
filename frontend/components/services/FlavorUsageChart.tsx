'use client';

import { useTranslations } from 'next-intl';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { format } from 'date-fns';

interface TimeSeriesPoint {
  timestamp: string;
  requests: number;
  tokens: number;
  cost: number;
}

interface FlavorUsageChartProps {
  data: TimeSeriesPoint[];
  period: '24h' | '7d' | '30d' | 'all';
}

export function FlavorUsageChart({ data, period }: FlavorUsageChartProps) {
  const t = useTranslations('flavors.analytics');

  // Format timestamp based on period
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    if (period === '24h') {
      return format(date, 'HH:mm');
    } else {
      return format(date, 'MMM dd');
    }
  };

  // Transform data for recharts
  const chartData = data.map((point) => ({
    ...point,
    formattedTimestamp: formatTimestamp(point.timestamp),
  }));

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={300}>
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
          />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="requests"
            stroke="hsl(var(--primary))"
            name={t('totalRequests')}
            strokeWidth={2}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="cost"
            stroke="hsl(var(--chart-2))"
            name={t('totalCost') + ' ($)'}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
