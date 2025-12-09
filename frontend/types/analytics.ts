/**
 * Analytics types for dashboard and service statistics.
 */

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'inactive';
export type AnalyticsPeriod = '24h' | '7d' | '30d' | 'all';

export interface DashboardOverview {
  total_jobs: number;
  successful_jobs: number;
  failed_jobs: number;
  success_rate: number;
  total_tokens: number;
  total_cost: number;
  active_services: number;
  avg_latency_ms: number;
}

export interface ServiceHealthSummary {
  service_id: string;
  service_name: string;
  requests_24h: number;
  success_rate: number;
  status: HealthStatus;
}

export interface RecentFailure {
  job_id: string;
  service_name: string;
  error: string;
  timestamp: string;
}

export interface DashboardAnalytics {
  period: '24h';
  overview: DashboardOverview;
  services: ServiceHealthSummary[];
  recent_failures: RecentFailure[];
  generated_at: string;
}

export interface ServiceStatsData {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  total_tokens: number;
  total_estimated_cost: number;
  avg_latency_ms: number;
  flavors_used: number;
  most_used_flavor: string | null;
}

export interface FlavorBreakdown {
  flavor_id: string;
  flavor_name: string;
  requests: number;
  percentage: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  requests: number;
  tokens: number;
  cost: number;
}

export interface ServiceStats {
  service_id: string;
  service_name: string;
  period: string;
  stats: ServiceStatsData;
  flavor_breakdown: FlavorBreakdown[];
  time_series: TimeSeriesPoint[];
  generated_at: string;
}
