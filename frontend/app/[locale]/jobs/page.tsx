'use client';

import { useState, useMemo, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useRouter, useParams } from 'next/navigation';
import { formatDistanceToNow, format } from 'date-fns';
import { ChevronDown, ChevronUp, Copy, Check, AlertCircle, XCircle, ExternalLink, Wifi, WifiOff, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Progress } from '@/components/ui/progress';
import { DataTable, type DataTableColumn } from '@/components/shared/DataTable';
import { EmptyState } from '@/components/shared/EmptyState';

import { useJobs, useCancelJob, useDeleteJob } from '@/hooks/use-jobs';
import { useJobsWebSocket } from '@/hooks/use-jobs-websocket';
import type { JobResponse, JobStatus, JobListFilters, JobProgress } from '@/types/job';

// Status badge variant mapping
const statusVariants: Record<JobStatus, 'default' | 'secondary' | 'destructive' | 'outline' | 'success'> = {
  queued: 'secondary',
  started: 'default',
  processing: 'default',
  completed: 'success',
  failed: 'destructive',
  cancelled: 'outline',
};

// Status options for filtering
const statusOptions: JobStatus[] = ['queued', 'started', 'processing', 'completed', 'failed', 'cancelled'];

export default function JobsPage() {
  const t = useTranslations('jobs');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const params = useParams();
  const locale = params.locale as string;

  // Filter state
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'all'>('all');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Expanded job details
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Build filters
  const filters: JobListFilters = {
    page,
    page_size: pageSize,
    ...(statusFilter !== 'all' && { status: statusFilter }),
  };

  const queryClient = useQueryClient();

  // Track known job IDs to detect new jobs
  const knownJobIdsRef = useRef<Set<string>>(new Set());

  // Callback when WebSocket receives a job update - refetch if it's a new job
  const handleJobUpdate = useCallback((jobId: string, status: JobStatus, _progress: JobProgress | null) => {
    // If this job ID is not in our known list and it's not terminal, it's a new job
    if (!knownJobIdsRef.current.has(jobId) && !['completed', 'failed', 'cancelled'].includes(status)) {
      // New job detected - invalidate query to fetch full job data
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
  }, [queryClient]);

  // Callback when job reaches terminal state - refetch to get final data
  const handleJobTerminal = useCallback((_jobId: string, _status: JobStatus) => {
    // Job completed/failed/cancelled - invalidate to fetch fresh data with final status
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
  }, [queryClient]);

  // WebSocket for real-time updates (declare first to use isConnected in polling)
  const { jobs: wsJobs, isConnected } = useJobsWebSocket({
    enabled: true,
    onJobUpdate: handleJobUpdate,
    onJobTerminal: handleJobTerminal,
  });

  // Fetch jobs - NO polling when WebSocket connected, fallback only
  const { data, isLoading, error } = useJobs(filters, {
    refetchInterval: isConnected ? false : 5000 // Only poll when WS disconnected
  });

  // Update known job IDs when data changes
  useMemo(() => {
    if (data?.items) {
      knownJobIdsRef.current = new Set(data.items.map(job => job.id));
    }
  }, [data?.items]);

  // Merge WebSocket updates with REST data
  const mergedItems = useMemo(() => {
    if (!data?.items) return [];

    return data.items.map((job) => {
      const wsUpdate = wsJobs.get(job.id);
      if (wsUpdate) {
        return {
          ...job,
          status: wsUpdate.status,
          progress: wsUpdate.progress,
        };
      }
      return job;
    });
  }, [data?.items, wsJobs]);

  // Cancel job mutation
  const cancelJobMutation = useCancelJob();

  // Delete job mutation
  const deleteJobMutation = useDeleteJob();

  // Handle job cancellation
  const handleCancelJob = async (jobId: string) => {
    try {
      await cancelJobMutation.mutateAsync(jobId);
      toast.success(t('cancelSuccess'));
    } catch (error: any) {
      toast.error(error.message || t('cancelError'));
    }
  };

  // Handle job deletion
  const handleDeleteJob = async (jobId: string) => {
    try {
      await deleteJobMutation.mutateAsync(jobId);
      toast.success(t('deleteSuccess'));
    } catch (error: any) {
      toast.error(error.message || t('deleteError'));
    }
  };

  // Calculate duration between created and completed
  const getDuration = (job: JobResponse): string => {
    if (!job.created_at) return '-';
    const start = new Date(job.created_at);
    const end = job.completed_at ? new Date(job.completed_at) : new Date();
    const diffMs = end.getTime() - start.getTime();
    const seconds = Math.floor(diffMs / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  // Copy job ID to clipboard
  const copyToClipboard = async (text: string, jobId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(jobId);
      toast.success(t('copySuccess'));
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      toast.error(t('copyError'));
    }
  };

  // Toggle expanded row
  const toggleExpanded = (jobId: string) => {
    setExpandedJobId((prev) => (prev === jobId ? null : jobId));
  };

  // Navigate to job detail page
  const navigateToDetail = (jobId: string) => {
    router.push(`/${locale}/jobs/${jobId}`);
  };

  // Table columns
  const columns: DataTableColumn<JobResponse>[] = [
    {
      header: t('jobId'),
      cell: (job) => (
        <div className="flex items-center gap-2">
          <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">
            {job.id.slice(0, 8)}...
          </code>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={(e) => {
              e.stopPropagation();
              copyToClipboard(job.id, job.id);
            }}
          >
            {copiedId === job.id ? (
              <Check className="h-3 w-3 text-green-500" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
          </Button>
        </div>
      ),
    },
    {
      header: t('serviceName'),
      cell: (job) => job.service_name,
    },
    {
      header: t('flavorName'),
      cell: (job) => job.flavor_name,
    },
    {
      header: tCommon('status'),
      cell: (job) => (
        <div className="flex flex-col gap-1">
          <Badge variant={statusVariants[job.status]}>
            {t(`status.${job.status}`)}
            {job.progress && (job.status === 'processing' || job.status === 'started') && (
              <span className="ml-1">({Math.round(job.progress.percentage)}%)</span>
            )}
          </Badge>
          {job.progress && (job.status === 'processing' || job.status === 'started') && (
            <>
              <Progress value={job.progress.percentage} className="h-1 w-20" />
              {job.progress.phase && job.progress.phase !== 'processing' && (
                <span className="text-xs text-muted-foreground">
                  {t(`phase.${job.progress.phase}`)}
                </span>
              )}
            </>
          )}
        </div>
      ),
    },
    {
      header: t('createdAt'),
      cell: (job) =>
        job.created_at
          ? formatDistanceToNow(new Date(job.created_at), { addSuffix: true })
          : '-',
    },
    {
      header: t('duration'),
      cell: (job) => getDuration(job),
    },
    {
      header: '',
      cell: (job) => {
        const isTerminal = ['completed', 'failed', 'cancelled'].includes(job.status);
        return (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={(e) => {
              e.stopPropagation();
              navigateToDetail(job.id);
            }}
            title={t('viewDetails')}
          >
            <ExternalLink className="h-4 w-4" />
          </Button>
          {(job.status === 'queued' || job.status === 'processing') && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-destructive hover:text-destructive"
              onClick={(e) => {
                e.stopPropagation();
                handleCancelJob(job.id);
              }}
              disabled={cancelJobMutation.isPending}
              title={t('cancel')}
            >
              <XCircle className="h-4 w-4" />
            </Button>
          )}
          {isTerminal && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                  onClick={(e) => e.stopPropagation()}
                  disabled={deleteJobMutation.isPending}
                  title={t('delete')}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                <AlertDialogHeader>
                  <AlertDialogTitle>{t('deleteConfirmTitle')}</AlertDialogTitle>
                  <AlertDialogDescription>
                    {t('deleteConfirmMessage')}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
                  <AlertDialogAction onClick={() => handleDeleteJob(job.id)}>
                    {t('delete')}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              toggleExpanded(job.id);
            }}
          >
            {expandedJobId === job.id ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>
        );
      },
      className: 'w-36',
    },
  ];

  // Job detail expanded row
  const JobDetail = ({ job }: { job: JobResponse }) => {
    return (
      <Card className="mt-2 mb-4 border-l-4 border-l-primary">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{t('viewDetails')}</CardTitle>
          <CardDescription>
            {job.created_at && format(new Date(job.created_at), 'PPpp')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Progress for active jobs */}
          {job.progress && (job.status === 'processing' || job.status === 'started') && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>{t('progress')}</span>
                <span>
                  {t('progressLabel', {
                    current: job.progress.current,
                    total: job.progress.total,
                    percentage: job.progress.percentage,
                  })}
                </span>
              </div>
              <Progress value={job.progress.percentage} />
            </div>
          )}

          {/* Error message for failed jobs */}
          {job.status === 'failed' && job.error && (
            <div className="flex items-start gap-2 p-3 bg-destructive/10 text-destructive rounded-md">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">{t('error')}</p>
                <p className="text-sm mt-1">{job.error}</p>
              </div>
            </div>
          )}

          {/* Result for completed jobs */}
          {job.status === 'completed' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{t('result')}</span>
                {job.result && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(
                      typeof job.result === 'string' ? job.result : JSON.stringify(job.result, null, 2),
                      `result-${job.id}`
                    )}
                  >
                    {copiedId === `result-${job.id}` ? (
                      <Check className="h-3 w-3 mr-1" />
                    ) : (
                      <Copy className="h-3 w-3 mr-1" />
                    )}
                    {t('copyResult')}
                  </Button>
                )}
              </div>
              {job.result ? (
                <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-64">
                  {typeof job.result === 'string'
                    ? job.result
                    : JSON.stringify(job.result, null, 2)}
                </pre>
              ) : (
                <p className="text-sm text-muted-foreground">{t('noResult')}</p>
              )}
            </div>
          )}

          {/* Timestamps */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">{t('createdAt')}</span>
              <p>{job.created_at ? format(new Date(job.created_at), 'PPpp') : '-'}</p>
            </div>
            {job.started_at && (
              <div>
                <span className="text-muted-foreground">{t('startedAt')}</span>
                <p>{format(new Date(job.started_at), 'PPpp')}</p>
              </div>
            )}
            {job.completed_at && (
              <div>
                <span className="text-muted-foreground">{t('completedAt')}</span>
                <p>{format(new Date(job.completed_at), 'PPpp')}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  // Render job rows with expandable details
  const renderJobsWithDetails = () => {
    if (!data?.items) return null;

    return (
      <div className="space-y-0">
        <DataTable
          columns={columns}
          data={mergedItems}
          isLoading={isLoading}
          getRowId={(job) => job.id}
          onRowClick={(job) => navigateToDetail(job.id)}
          emptyState={{
            title: t('emptyState'),
            description: t('emptyStateDescription'),
          }}
          pagination={{
            page,
            pageSize,
            total: data.total,
            totalPages: data.total_pages,
            onPageChange: setPage,
            onPageSizeChange: (newSize) => {
              setPageSize(newSize);
              setPage(1);
            },
          }}
        />
        {/* Expanded details rendered outside table */}
        {expandedJobId && mergedItems.find((j) => j.id === expandedJobId) && (
          <JobDetail job={mergedItems.find((j) => j.id === expandedJobId)!} />
        )}
      </div>
    );
  };

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
          <p className="text-muted-foreground">{t('subtitle')}</p>
        </div>
        <EmptyState
          title={t('error')}
          description={t('unknownError')}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
          <p className="text-muted-foreground">{t('subtitle')}</p>
        </div>
        {/* WebSocket Connection Status */}
        <div className="flex items-center gap-2">
          {isConnected ? (
            <div className="flex items-center text-xs text-green-600">
              <Wifi className="h-3 w-3 mr-1" />
              {t('websocketConnected')}
            </div>
          ) : (
            <div className="flex items-center text-xs text-muted-foreground">
              <WifiOff className="h-3 w-3 mr-1" />
              {t('websocketDisconnected')}
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="w-48">
          <Select
            value={statusFilter}
            onValueChange={(value) => {
              setStatusFilter(value as JobStatus | 'all');
              setPage(1);
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder={t('filterByStatus')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('allStatuses')}</SelectItem>
              {statusOptions.map((status) => (
                <SelectItem key={status} value={status}>
                  {t(`status.${status}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Jobs Table */}
      {renderJobsWithDetails()}
    </div>
  );
}
