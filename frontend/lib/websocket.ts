import { getConfigSync, buildWsUrl } from './config';

export interface JobUpdate {
  job_id: string;
  status: 'queued' | 'started' | 'processing' | 'completed' | 'failed';
  progress?: {
    current: number;
    total: number;
    percentage: number;
  };
  result?: any;
  error?: string;
  timestamp: string;
}

export class JobMonitorClient {
  private ws: WebSocket | null = null;
  private jobId: string;
  private wsBaseUrl: string;
  private onMessage: (data: JobUpdate) => void;
  private onError?: (error: Event) => void;
  private onClose?: () => void;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;

  constructor(
    jobId: string,
    onMessage: (data: JobUpdate) => void,
    onError?: (error: Event) => void,
    onClose?: () => void,
    wsBaseUrl?: string
  ) {
    this.jobId = jobId;
    this.onMessage = onMessage;
    this.onError = onError;
    this.onClose = onClose;

    // Use provided wsBaseUrl or derive from config
    if (wsBaseUrl) {
      this.wsBaseUrl = wsBaseUrl;
    } else {
      const config = getConfigSync();
      if (!config) {
        throw new Error('Config not loaded. Ensure ConfigProvider has initialized.');
      }
      this.wsBaseUrl = buildWsUrl(config);
    }
  }

  connect() {
    try {
      const wsUrl = `${this.wsBaseUrl}/ws/jobs/${this.jobId}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data: JobUpdate = JSON.parse(event.data);
          this.onMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (this.onError) {
          this.onError(error);
        }
      };

      this.ws.onclose = () => {
        if (this.onClose) {
          this.onClose();
        }

        // Attempt to reconnect if not intentionally closed
        if (
          this.reconnectAttempts < this.maxReconnectAttempts &&
          this.ws?.readyState !== WebSocket.CLOSING
        ) {
          this.reconnectAttempts++;
          setTimeout(() => this.connect(), this.reconnectDelay);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      if (this.onError) {
        this.onError(error as Event);
      }
    }
  }

  disconnect() {
    if (this.ws) {
      this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
      this.ws.close();
      this.ws = null;
    }
  }

  getReadyState(): number | null {
    return this.ws?.readyState ?? null;
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
