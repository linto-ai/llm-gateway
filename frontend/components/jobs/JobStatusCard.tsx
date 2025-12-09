'use client';

import { useTranslations } from 'next-intl';
import { Wifi, WifiOff, Loader2, Clock } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import type { JobStatus, JobProgress } from '@/types/job';

// Helper function to format duration in seconds
function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
}

interface JobStatusCardProps {
  status: JobStatus;
  progress: JobProgress | null;
  isConnected: boolean;
  duration?: string;
}

// Status badge variant mapping
const statusVariants: Record<JobStatus, 'default' | 'secondary' | 'destructive' | 'outline' | 'success'> = {
  queued: 'secondary',
  started: 'default',
  processing: 'default',
  completed: 'success',
  failed: 'destructive',
  cancelled: 'outline',
};

export function JobStatusCard({
  status,
  progress,
  isConnected,
  duration,
}: JobStatusCardProps) {
  const t = useTranslations('jobs');

  const isActiveJob = ['queued', 'started', 'processing'].includes(status);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{t('status.label')}</CardTitle>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <div className="flex items-center gap-1 text-xs text-green-600">
                <Wifi className="h-3 w-3" />
                <span>{t('websocketConnected')}</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <WifiOff className="h-3 w-3" />
                <span>{t('websocketDisconnected')}</span>
              </div>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant={statusVariants[status]} className="text-sm">
              {t(`status.${status}`)}
            </Badge>
            {isActiveJob && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </div>
          {duration && (
            <span className="text-sm text-muted-foreground">
              {t('duration')}: {duration}
            </span>
          )}
        </div>

        {/* Progress bar for active jobs */}
        {progress && isActiveJob && (
          <div className="space-y-2">
            {/* Phase and batch info */}
            {progress.phase && (
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  {/* Enhanced reduce phase display */}
                  {progress.phase === 'reducing' && progress.reduce_level !== undefined ? (
                    <Badge variant="outline">
                      {progress.reduce_batch
                        ? t('phase.reducingBatch', {
                            level: progress.reduce_level,
                            items: progress.reduce_items ?? 0,
                            batch: progress.reduce_batch,
                          })
                        : t('phase.reducingLevel', {
                            level: progress.reduce_level,
                            items: progress.reduce_items ?? 0,
                          })}
                    </Badge>
                  ) : (
                    <Badge variant="outline">{t(`phase.${progress.phase}`)}</Badge>
                  )}
                  {progress.total_batches && progress.total_batches > 1 && progress.phase !== 'reducing' && (
                    <span className="text-muted-foreground">
                      {t('batch', {
                        current: progress.current_batch || 1,
                        total: progress.total_batches,
                      })}
                    </span>
                  )}
                </div>
                {progress.estimated_seconds_remaining != null && progress.estimated_seconds_remaining > 0 && (
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>{t('eta', { time: formatDuration(progress.estimated_seconds_remaining) })}</span>
                  </div>
                )}
              </div>
            )}

            {/* Progress bar */}
            <div className="flex justify-between text-sm">
              <span>{t('progress')}</span>
              <span>
                {progress.total_turns && progress.total_turns > 0
                  ? t('progressLabel', {
                      current: progress.completed_turns || progress.current,
                      total: progress.total_turns || progress.total,
                      percentage: Math.round(progress.percentage),
                    })
                  : `${Math.round(progress.percentage)}%`}
              </span>
            </div>
            <Progress value={progress.percentage} className="h-2" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
