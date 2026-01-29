/**
 * Runtime configuration utilities.
 * Fetches config from /api/config at runtime, enabling true runtime configuration
 * without build-time placeholders or sed hacks.
 */

export interface RuntimeConfig {
  apiUrl: string;
  wsUrl: string;
  basePath: string;
  appName: string;
}

export interface ConfigContextValue extends RuntimeConfig {
  isLoading: boolean;
}

let cachedConfig: RuntimeConfig | null = null;

/**
 * Fetches runtime configuration from the API route.
 * Caches the result for subsequent calls within the same session.
 */
export async function getConfig(): Promise<RuntimeConfig> {
  if (cachedConfig) {
    return cachedConfig;
  }

  try {
    const response = await fetch('/api/config');
    if (!response.ok) {
      throw new Error(`Config fetch failed: ${response.status}`);
    }
    cachedConfig = await response.json();
    return cachedConfig!;
  } catch (error) {
    console.error('Failed to fetch runtime config:', error);
    // Return defaults on error
    return {
      apiUrl: '',
      wsUrl: '',
      basePath: '',
      appName: 'LLM Gateway',
    };
  }
}

/**
 * Returns cached config synchronously, or null if not yet loaded.
 * Use this in contexts where async fetch is not possible.
 */
export function getConfigSync(): RuntimeConfig | null {
  return cachedConfig;
}

/**
 * Sets the cached config. Used by ConfigProvider after initial fetch.
 */
export function setConfigCache(config: RuntimeConfig): void {
  cachedConfig = config;
}

/**
 * Builds the API base URL from config.
 * If apiUrl is set, returns it directly.
 * Otherwise, derives from window.location for same-origin deployments.
 */
export function buildApiUrl(config: RuntimeConfig): string {
  if (config.apiUrl) {
    return config.apiUrl;
  }

  // Auto-detect from window.location for same-origin deployments (K3S)
  if (typeof window !== 'undefined') {
    const { origin } = window.location;
    const basePath = config.basePath || '';
    return `${origin}${basePath}/api`;
  }

  // Server-side fallback
  return '';
}

/**
 * Builds the WebSocket base URL from config.
 * If wsUrl is set, returns it directly.
 * Otherwise, derives from window.location for same-origin deployments.
 */
export function buildWsUrl(config: RuntimeConfig): string {
  if (config.wsUrl) {
    return config.wsUrl;
  }

  // Auto-detect from window.location for same-origin deployments (K3S)
  if (typeof window !== 'undefined') {
    const { protocol, host } = window.location;
    const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
    const basePath = config.basePath || '';
    return `${wsProtocol}//${host}${basePath}`;
  }

  // Server-side fallback
  return '';
}
