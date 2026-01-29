import { useEffect, useState, useRef, useCallback } from 'react';
import { useConfig } from '@/components/providers/ConfigProvider';
import { buildWsUrl } from '@/lib/config';
import type {
  JobStatus,
  JobProgress,
  JobUpdate,
  CurrentPassMetrics,
  CumulativeMetrics,
} from '@/types/job';

interface UseJobWebSocketOptions {
  onStatusChange?: (update: JobUpdate) => void;
  enabled?: boolean;
}

interface UseJobWebSocketReturn {
  status: JobStatus | null;
  progress: JobProgress | null;
  result: any | null;
  error: string | null;
  isConnected: boolean;
  lastUpdate: JobUpdate | null;
  // Token metrics
  currentPassMetrics: CurrentPassMetrics | null;
  cumulativeMetrics: CumulativeMetrics | null;
}

/**
 * React hook for WebSocket-based job monitoring
 * Connects to /ws/jobs/{job_id} and receives real-time updates
 */
export function useJobWebSocket(
  jobId: string | null,
  options?: UseJobWebSocketOptions
): UseJobWebSocketReturn {
  const { onStatusChange, enabled = true } = options || {};
  const config = useConfig();

  const [status, setStatus] = useState<JobStatus | null>(null);
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<JobUpdate | null>(null);
  // Token metrics state
  const [currentPassMetrics, setCurrentPassMetrics] = useState<CurrentPassMetrics | null>(null);
  const [cumulativeMetrics, setCumulativeMetrics] = useState<CumulativeMetrics | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 2000;
  const shouldReconnectRef = useRef(true);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const update: JobUpdate = JSON.parse(event.data);
        setLastUpdate(update);
        setStatus(update.status);

        if (update.progress) {
          setProgress(update.progress);
        }

        if (update.result !== undefined) {
          setResult(update.result);
        }

        if (update.error) {
          setError(update.error);
        }

        // Handle token metrics updates
        if (update.current_pass_metrics) {
          setCurrentPassMetrics(update.current_pass_metrics);
        }

        if (update.cumulative_metrics) {
          setCumulativeMetrics(update.cumulative_metrics);
        }

        // Call callback if provided
        if (onStatusChange) {
          onStatusChange(update);
        }

        // If terminal state, stop reconnecting
        if (['completed', 'failed', 'cancelled'].includes(update.status)) {
          shouldReconnectRef.current = false;
        }
      } catch {
        // Ignore malformed messages
      }
    },
    [onStatusChange]
  );

  const connect = useCallback(() => {
    if (!jobId || !enabled || config.isLoading) return;

    try {
      const wsBaseUrl = buildWsUrl(config);
      const wsUrl = `${wsBaseUrl}/ws/jobs/${jobId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = handleMessage;

      ws.onerror = () => {
        // WebSocket errors don't provide detailed info in browsers
        // The actual error will come through onclose or onmessage
      };

      ws.onclose = (event) => {
        setIsConnected(false);

        // Normal closure (1000) or policy violation (1008) = don't reconnect
        if (event.code === 1000 || event.code === 1008) {
          shouldReconnectRef.current = false;
          return;
        }

        // Attempt to reconnect if not intentionally closed and not in terminal state
        if (
          shouldReconnectRef.current &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          reconnectAttemptsRef.current++;
          setTimeout(() => connect(), reconnectDelay);
        }
      };
    } catch {
      // WebSocket connection failed
    }
  }, [jobId, enabled, config, handleMessage]);

  // Connect on mount or when jobId changes (wait for config to load)
  useEffect(() => {
    if (!jobId || !enabled || config.isLoading) return;

    // Reset state for new job
    setStatus(null);
    setProgress(null);
    setResult(null);
    setError(null);
    setLastUpdate(null);
    // Reset token metrics state
    setCurrentPassMetrics(null);
    setCumulativeMetrics(null);
    shouldReconnectRef.current = true;
    reconnectAttemptsRef.current = 0;

    connect();

    // Cleanup on unmount
    return () => {
      shouldReconnectRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [jobId, enabled, config.isLoading, connect]);

  return {
    status,
    progress,
    result,
    error,
    isConnected,
    lastUpdate,
    // Token metrics
    currentPassMetrics,
    cumulativeMetrics,
  };
}
