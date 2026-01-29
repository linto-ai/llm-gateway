import { useEffect, useState, useRef, useCallback } from 'react';
import { useConfig } from '@/components/providers/ConfigProvider';
import { buildWsUrl } from '@/lib/config';
import type {
  JobStatus,
  JobProgress,
  ActiveJobSnapshot,
  JobsWebSocketMessage,
} from '@/types/job';

interface UseJobsWebSocketOptions {
  enabled?: boolean;
  onJobUpdate?: (jobId: string, status: JobStatus, progress: JobProgress | null) => void;
  onJobTerminal?: (jobId: string, status: JobStatus) => void;
}

interface UseJobsWebSocketReturn {
  /** Map of job_id -> latest status/progress */
  jobs: Map<string, ActiveJobSnapshot>;
  /** Whether WebSocket is connected */
  isConnected: boolean;
  /** List of active job IDs */
  activeJobIds: string[];
  /** Get update for specific job */
  getJobUpdate: (jobId: string) => ActiveJobSnapshot | undefined;
}

/**
 * React hook for global jobs WebSocket monitoring.
 * Connects to /ws/jobs and receives updates for ALL active jobs.
 */
export function useJobsWebSocket(
  options?: UseJobsWebSocketOptions
): UseJobsWebSocketReturn {
  const { enabled = true, onJobUpdate, onJobTerminal } = options || {};
  const config = useConfig();

  const [jobs, setJobs] = useState<Map<string, ActiveJobSnapshot>>(new Map());
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;
  const shouldReconnectRef = useRef(true);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: JobsWebSocketMessage = JSON.parse(event.data);

        if (message.type === 'jobs_snapshot') {
          // Initial snapshot - replace all tracked jobs
          const newJobs = new Map<string, ActiveJobSnapshot>();
          for (const job of message.jobs) {
            newJobs.set(job.job_id, job);
          }
          setJobs(newJobs);
        } else if (message.type === 'job_update') {
          // Individual update
          setJobs((prev) => {
            const next = new Map(prev);

            // If terminal state, remove from tracking
            if (['completed', 'failed', 'cancelled'].includes(message.status)) {
              next.delete(message.job_id);
            } else {
              // Update or add job
              next.set(message.job_id, {
                job_id: message.job_id,
                status: message.status,
                progress: message.progress,
              });
            }

            return next;
          });

          // Call callbacks if provided
          if (onJobUpdate) {
            onJobUpdate(message.job_id, message.status, message.progress);
          }

          // Notify on terminal state so consumer can refetch fresh data
          if (['completed', 'failed', 'cancelled'].includes(message.status) && onJobTerminal) {
            onJobTerminal(message.job_id, message.status);
          }
        }
      } catch {
        // Ignore malformed messages
      }
    },
    [onJobUpdate, onJobTerminal]
  );

  const connect = useCallback(() => {
    if (!enabled || config.isLoading) return;

    try {
      const wsBaseUrl = buildWsUrl(config);
      const wsUrl = `${wsBaseUrl}/ws/jobs`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = handleMessage;

      ws.onerror = () => {
        // WebSocket errors don't provide detailed info in browsers
      };

      ws.onclose = (event) => {
        setIsConnected(false);

        // Normal closure = don't reconnect
        if (event.code === 1000) {
          return;
        }

        // Attempt reconnect
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
  }, [enabled, config, handleMessage]);

  // Connect on mount (wait for config to load)
  useEffect(() => {
    if (!enabled || config.isLoading) return;

    shouldReconnectRef.current = true;
    reconnectAttemptsRef.current = 0;
    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [enabled, config.isLoading, connect]);

  // Derived state
  const activeJobIds = Array.from(jobs.keys());

  const getJobUpdate = useCallback(
    (jobId: string) => jobs.get(jobId),
    [jobs]
  );

  return {
    jobs,
    isConnected,
    activeJobIds,
    getJobUpdate,
  };
}
