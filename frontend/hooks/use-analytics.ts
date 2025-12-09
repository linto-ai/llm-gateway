import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { DashboardAnalytics, ServiceStats, AnalyticsPeriod } from '@/types/analytics';

/**
 * TanStack Query hooks for analytics data.
 */

/**
 * Fetch dashboard analytics (24h fixed period).
 * Returns system-wide health overview.
 */
export function useDashboardAnalytics() {
  return useQuery({
    queryKey: ['analytics', 'dashboard'],
    queryFn: async () => {
      return apiClient.get<DashboardAnalytics>('/api/v1/analytics/dashboard');
    },
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Fetch service-level statistics with configurable period.
 * Returns aggregated statistics across all flavors for a service.
 */
export function useServiceStats(serviceId: string, period: AnalyticsPeriod = '24h') {
  return useQuery({
    queryKey: ['services', serviceId, 'stats', period],
    queryFn: async () => {
      return apiClient.get<ServiceStats>(
        `/api/v1/services/${serviceId}/stats`,
        { params: { period } }
      );
    },
    enabled: !!serviceId,
  });
}
