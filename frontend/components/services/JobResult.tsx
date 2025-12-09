'use client';

import { Loader2, Copy, AlertCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import type { JobResponse } from '@/types/job';

interface JobResultProps {
  job: JobResponse | undefined | null;
  isLoading: boolean;
}

export function JobResult({ job, isLoading }: JobResultProps) {
  const t = useTranslations();

  const formatDate = (dateString: string | undefined | null): string => {
    if (!dateString) return '-';
    try {
      return new Intl.DateTimeFormat('default', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(dateString));
    } catch {
      return '-';
    }
  };

  const getStatusVariant = (
    status?: string
  ): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (status) {
      case 'completed':
        return 'default';
      case 'failed':
        return 'destructive';
      case 'processing':
        return 'secondary';
      case 'queued':
      case 'started':
      default:
        return 'outline';
    }
  };

  const handleCopyResult = async () => {
    if (job?.result) {
      try {
        await navigator.clipboard.writeText(
          typeof job.result === 'string' ? job.result : JSON.stringify(job.result, null, 2)
        );
        toast.success(t('jobs.copySuccess'));
      } catch (error) {
        toast.error(t('jobs.copyError'));
      }
    }
  };

  return (
    <Card className="mt-6">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{t('jobs.title')}</CardTitle>
          {job?.status && (
            <Badge variant={getStatusVariant(job.status)}>
              {t(`jobs.status.${job.status}`)}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && !job && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="ml-3 text-muted-foreground">{t('jobs.loading')}</p>
          </div>
        )}

        {job?.status === 'processing' && job.progress && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>{t('jobs.progress')}</span>
              <span>{job.progress.percentage}%</span>
            </div>
            <Progress value={job.progress.percentage} />
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>
                {job.progress.current} / {job.progress.total}
              </span>
              {job.progress.phase && (
                <Badge variant="outline" className="text-xs">
                  {/* Enhanced reduce phase display */}
                  {job.progress.phase === 'reducing' && job.progress.reduce_level !== undefined
                    ? (job.progress.reduce_batch
                        ? t('jobs.phase.reducingBatch', {
                            level: job.progress.reduce_level,
                            items: job.progress.reduce_items ?? 0,
                            batch: job.progress.reduce_batch,
                          })
                        : t('jobs.phase.reducingLevel', {
                            level: job.progress.reduce_level,
                            items: job.progress.reduce_items ?? 0,
                          }))
                    : t(`jobs.phase.${job.progress.phase}`)}
                </Badge>
              )}
            </div>
          </div>
        )}

        {(job?.status === 'queued' || job?.status === 'started') && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="ml-3 text-sm">{t('jobs.waiting')}</p>
          </div>
        )}

        {job?.status === 'completed' && job.result && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium">{t('jobs.result')}</h3>
                <Button variant="outline" size="sm" onClick={handleCopyResult}>
                  <Copy className="mr-2 h-4 w-4" />
                  {t('jobs.copyResult')}
                </Button>
              </div>
              <ScrollArea className="h-96 rounded-md border p-4 bg-muted/50">
                <pre className="whitespace-pre-wrap text-sm font-mono">
                  {typeof job.result === 'string'
                    ? job.result
                    : JSON.stringify(job.result, null, 2)}
                </pre>
              </ScrollArea>
            </div>
          </div>
        )}

        {job?.status === 'failed' && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>{t('jobs.failed')}</AlertTitle>
            <AlertDescription>{job.error || t('jobs.unknownError')}</AlertDescription>
          </Alert>
        )}

        {job && (
          <div className="mt-6 pt-4 border-t text-xs text-muted-foreground space-y-1">
            <div className="flex justify-between">
              <span>{t('jobs.serviceName')}:</span>
              <span className="font-medium">{job.service_name}</span>
            </div>
            <div className="flex justify-between">
              <span>{t('jobs.flavorName')}:</span>
              <span className="font-medium">{job.flavor_name}</span>
            </div>
            <div className="flex justify-between">
              <span>{t('jobs.createdAt')}:</span>
              <span>{formatDate(job.created_at)}</span>
            </div>
            {job.started_at && (
              <div className="flex justify-between">
                <span>{t('jobs.startedAt')}:</span>
                <span>{formatDate(job.started_at)}</span>
              </div>
            )}
            {job.completed_at && (
              <div className="flex justify-between">
                <span>{t('jobs.completedAt')}:</span>
                <span>{formatDate(job.completed_at)}</span>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
