import axios, { AxiosError, AxiosInstance, AxiosResponse } from 'axios';
import { getConfigSync, buildApiUrl } from './config';

let _api: AxiosInstance | null = null;

function createApiInstance(baseURL: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor
  instance.interceptors.request.use(
    (config) => {
      // Future: Add authentication token
      // const token = getAuthToken();
      // if (token) {
      //   config.headers.Authorization = `Bearer ${token}`;
      // }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      return response.data;
    },
    (error: AxiosError) => {
      // Extract error message, handling various FastAPI error formats
      const detail = (error.response?.data as any)?.detail;
      let message: string;

      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        // FastAPI validation errors are arrays of {type, loc, msg, input}
        message = detail.map((err: any) => err.msg || String(err)).join(', ');
      } else if (detail && typeof detail === 'object') {
        message = detail.msg || detail.message || JSON.stringify(detail);
      } else {
        message = error.message || 'An error occurred';
      }

      return Promise.reject({
        ...error,
        message,
        status: error.response?.status,
      });
    }
  );

  return instance;
}

/**
 * Get the API client instance.
 * Lazily initializes using the runtime config.
 * Throws if config is not yet loaded.
 */
export function getApi(): AxiosInstance {
  if (!_api) {
    const config = getConfigSync();
    if (!config) {
      throw new Error('Config not loaded. Ensure ConfigProvider has initialized.');
    }
    const baseURL = buildApiUrl(config);
    _api = createApiInstance(baseURL);
  }
  return _api;
}

/**
 * Legacy export for backward compatibility.
 * Uses a Proxy to defer initialization until first use.
 */
export const api = new Proxy({} as AxiosInstance, {
  get(_target, prop) {
    return getApi()[prop as keyof AxiosInstance];
  },
});

export type ApiError = {
  message: string;
  status?: number;
  response?: {
    data?: {
      detail?: string;
    };
  };
};
