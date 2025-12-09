/**
 * Number formatting utilities for consistent display across the application.
 */

/**
 * Format large token counts with SI suffixes.
 * - Values < 1000: show as-is (e.g., 523)
 * - Values >= 1000 and < 1M: use 'k' (e.g., 1.2k, 10k, 123k)
 * - Values >= 1M: use 'M' (e.g., 1.2M, 12M)
 */
export function formatTokenCount(value: number): string {
  if (value < 1000) {
    return value.toString();
  }
  if (value < 1_000_000) {
    const kValue = value / 1000;
    // Show 1 decimal if < 10k, otherwise round
    if (kValue < 10) {
      return `${kValue.toFixed(1)}k`;
    }
    return `${Math.round(kValue)}k`;
  }
  // Values >= 1M
  const mValue = value / 1_000_000;
  if (mValue < 10) {
    return `${mValue.toFixed(1)}M`;
  }
  return `${Math.round(mValue)}M`;
}

/**
 * Format cost values in USD.
 * - Values < 0.01: show 4 decimals (e.g., $0.0012)
 * - Values < 1: show 3 decimals (e.g., $0.123)
 * - Values >= 1: show 2 decimals (e.g., $45.67)
 */
export function formatCost(value: number): string {
  if (value < 0.01) {
    return `$${value.toFixed(4)}`;
  }
  if (value < 1) {
    return `$${value.toFixed(3)}`;
  }
  return `$${value.toFixed(2)}`;
}

/**
 * Format latency/duration values.
 * - Values < 1000ms: show in ms (e.g., 500ms)
 * - Values >= 1000ms: show in seconds (e.g., 1.5s, 12.3s)
 */
export function formatLatency(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  const seconds = ms / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
}
