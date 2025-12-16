import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d);
}

export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}

// Model limits utilities

/**
 * Format token count for display (e.g., 128000 -> "128K", 1000000 -> "1M")
 */
export function formatTokens(count: number | undefined | null): string {
  if (!count) return '-';
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
  if (count >= 1000) return `${Math.round(count / 1000)}K`;
  return count.toLocaleString();
}

/**
 * Get model limits (simplified - direct values only, no overrides)
 */
export function getEffectiveModelLimits(model: {
  context_length: number;
  max_generation_length: number;
}): {
  contextLength: number;
  maxGeneration: number;
} {
  return {
    contextLength: model.context_length,
    maxGeneration: model.max_generation_length,
  };
}

// TTL (Time To Live) utilities

export type TtlUnit = 'seconds' | 'minutes' | 'hours' | 'days';

const TTL_MULTIPLIERS: Record<TtlUnit, number> = {
  seconds: 1,
  minutes: 60,
  hours: 3600,
  days: 86400,
};

/**
 * Convert a duration value with unit to seconds
 */
export function ttlToSeconds(value: number, unit: TtlUnit): number {
  return value * TTL_MULTIPLIERS[unit];
}

/**
 * Convert seconds to the most appropriate unit with value
 */
export function secondsToTtl(seconds: number): { value: number; unit: TtlUnit } {
  if (seconds % 86400 === 0 && seconds >= 86400) {
    return { value: seconds / 86400, unit: 'days' };
  }
  if (seconds % 3600 === 0 && seconds >= 3600) {
    return { value: seconds / 3600, unit: 'hours' };
  }
  if (seconds % 60 === 0 && seconds >= 60) {
    return { value: seconds / 60, unit: 'minutes' };
  }
  return { value: seconds, unit: 'seconds' };
}

/**
 * Format a TTL duration in seconds to a human-readable string
 * Note: This returns the English format; for i18n use the translation keys instead
 */
export function formatTtlDuration(seconds: number): string {
  if (seconds >= 86400) {
    const days = Math.floor(seconds / 86400);
    return `${days} ${days === 1 ? 'day' : 'days'}`;
  }
  if (seconds >= 3600) {
    const hours = Math.floor(seconds / 3600);
    return `${hours} ${hours === 1 ? 'hour' : 'hours'}`;
  }
  if (seconds >= 60) {
    const minutes = Math.floor(seconds / 60);
    return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
  }
  return `${seconds} ${seconds === 1 ? 'second' : 'seconds'}`;
}

/**
 * Check if a date is expired (past now)
 */
export function isExpired(expiresAt: string | Date | null | undefined): boolean {
  if (!expiresAt) return false;
  const expiresDate = typeof expiresAt === 'string' ? new Date(expiresAt) : expiresAt;
  return expiresDate < new Date();
}

/**
 * Check if a date is expiring soon (within specified hours, default 24)
 */
export function isExpiringSoon(expiresAt: string | Date | null | undefined, withinHours: number = 24): boolean {
  if (!expiresAt) return false;
  const expiresDate = typeof expiresAt === 'string' ? new Date(expiresAt) : expiresAt;
  const now = new Date();
  if (expiresDate < now) return false; // Already expired
  const hoursUntilExpiry = (expiresDate.getTime() - now.getTime()) / (1000 * 60 * 60);
  return hoursUntilExpiry < withinHours;
}
