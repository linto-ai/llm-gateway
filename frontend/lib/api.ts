import axios, { AxiosError, AxiosResponse } from 'axios';
import { API_BASE_URL } from './constants';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
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
api.interceptors.response.use(
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

export type ApiError = {
  message: string;
  status?: number;
  response?: {
    data?: {
      detail?: string;
    };
  };
};
