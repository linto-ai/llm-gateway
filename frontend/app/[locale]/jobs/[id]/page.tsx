'use client';

import { use, useMemo, useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, RefreshCw, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
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
import { EmptyState } from '@/components/shared/EmptyState';
import {
  JobStatusCard,
  JobResultView,
  JobMetadata,
  JobMetricsCard,
  JobProcessingTimeline,
  JobResultEditor,
  JobVersionHistory,
  MetadataDisplay,
  CategorizationDisplay,
} from '@/components/jobs';

import { useJob, useDeleteJob } from '@/hooks/use-jobs';
import { useJobWebSocket } from '@/hooks/use-job-websocket';
import { useUpdateJobResult, useRestoreJobVersion } from '@/hooks/use-job-versions';
import { useExtractJobMetadata } from '@/hooks/use-document-templates';
import type { JobResponse, JobStatus, JobTokenMetrics, CumulativeMetrics } from '@/types/job';

interface JobDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function JobDetailPage({ params }: JobDetailPageProps) {
  const { id } = use(params);
  const t = useTranslations('jobs');
  const router = useRouter();
  const queryClient = useQueryClient();

  // Determine if job is in a terminal state to stop polling
  const isTerminalState = (status: JobStatus | undefined | null) =>
    status ? ['completed', 'failed', 'cancelled'].includes(status) : false;

  // Callback when job reaches terminal state via WebSocket - refetch to get complete data
  const handleStatusChange = useCallback((update: import('@/types/job').JobUpdate) => {
    if (['completed', 'failed', 'cancelled'].includes(update.status)) {
      // Job finished - invalidate cache to fetch complete data including token_metrics
      queryClient.invalidateQueries({ queryKey: ['jobs', id] });
    }
  }, [queryClient, id]);

  // WebSocket for real-time updates (declare first to use isConnected in polling)
  const {
    status: wsStatus,
    progress: wsProgress,
    result: wsResult,
    error: wsError,
    isConnected,
    currentPassMetrics,
    cumulativeMetrics,
  } = useJobWebSocket(id, {
    enabled: true, // Always try to connect, hook handles terminal states internally
    onStatusChange: handleStatusChange,
  });

  // Fetch job data ONLY as fallback when WebSocket is NOT connected
  // WebSocket provides real-time updates, polling is redundant when WS works
  const { data: job, isLoading, error } = useJob(id, {
    refetchInterval: (data) => {
      // Stop polling if terminal state (from REST or WebSocket)
      if (isTerminalState(data?.status) || isTerminalState(wsStatus)) {
        return false;
      }
      // If WebSocket is connected, NO polling needed - WS handles updates
      if (isConnected) {
        return false;
      }
      // WebSocket not connected - use polling as fallback
      return 2000;
    },
  });

  // Merge WebSocket updates with REST data
  // WebSocket takes priority during processing, but for terminal states use REST data
  // (REST data is the source of truth after edits/restores)
  const currentStatus = wsStatus || job?.status || 'queued';
  const currentProgress = wsProgress || job?.progress || null;
  const isTerminal = isTerminalState(currentStatus);
  // For terminal jobs, prefer REST data (updated by edits); for active jobs, prefer WebSocket
  const currentResult = isTerminal ? (job?.result ?? wsResult) : (wsResult ?? job?.result);
  const currentError = wsError || job?.error || null;

  // Determine if job is active (for live metrics display)
  const isActiveJob = ['queued', 'started', 'processing'].includes(currentStatus);

  // Edit and version history state
  const [isEditing, setIsEditing] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Mutations for editing, restoring and deleting
  const updateResultMutation = useUpdateJobResult(id);
  const restoreVersionMutation = useRestoreJobVersion(id);
  const extractMetadataMutation = useExtractJobMetadata();
  const deleteJobMutation = useDeleteJob();

  // Build current token metrics from WebSocket cumulative data for live display
  // When job is complete, use the full token_metrics from REST API
  const currentTokenMetrics: JobTokenMetrics | CumulativeMetrics | null = useMemo(() => {
    if (cumulativeMetrics) {
      return cumulativeMetrics;
    }
    return job?.token_metrics || null;
  }, [cumulativeMetrics, job?.token_metrics]);

  // Calculate duration
  const duration = useMemo(() => {
    if (!job?.created_at) return undefined;
    const start = new Date(job.created_at);
    const end = job?.completed_at ? new Date(job.completed_at) : new Date();
    const diffMs = end.getTime() - start.getTime();
    const seconds = Math.floor(diffMs / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  }, [job?.created_at, job?.completed_at]);

  // Extract content from result for editing
  const extractedContent = useMemo(() => {
    if (!currentResult) return '';
    if (typeof currentResult === 'string') return currentResult;
    if (typeof currentResult === 'object' && currentResult.output) {
      return currentResult.output;
    }
    return JSON.stringify(currentResult, null, 2);
  }, [currentResult]);

  // Handle save from editor
  const handleSaveEdit = useCallback(async (content: string) => {
    try {
      await updateResultMutation.mutateAsync(content);
      setIsEditing(false);
      toast.success(t('editor.saveSuccess'));
    } catch (error: any) {
      toast.error(error.message || t('editor.saveError'));
      throw error; // Re-throw so editor knows save failed
    }
  }, [updateResultMutation, t]);

  // Handle restore from version history
  const handleRestoreVersion = useCallback(async (versionNumber: number) => {
    try {
      await restoreVersionMutation.mutateAsync(versionNumber);
      toast.success(t('versions.restoreSuccess', { number: versionNumber }));
    } catch (error: any) {
      toast.error(error.message || t('versions.restoreError'));
      throw error;
    }
  }, [restoreVersionMutation, t]);

  // Handle delete job
  const handleDeleteJob = useCallback(async () => {
    try {
      await deleteJobMutation.mutateAsync(id);
      toast.success(t('deleteSuccess'));
      // Get locale from params and redirect with locale prefix
      const params = new URLSearchParams(window.location.search);
      const pathParts = window.location.pathname.split('/');
      const locale = pathParts[1] || 'en';
      router.push(`/${locale}/jobs`);
    } catch (error: any) {
      toast.error(error.message || t('deleteError'));
    }
  }, [deleteJobMutation, id, t, router]);

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('backToList')}
          </Button>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="animate-pulse text-muted-foreground">{t('loading')}</div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !job) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('backToList')}
          </Button>
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
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('backToList')}
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{t('detailTitle')}</h1>
            <p className="text-muted-foreground text-sm">
              {job.service_name} / {job.flavor_name}
            </p>
          </div>
        </div>

        {/* Delete button - only for terminal states */}
        {isTerminal && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm" disabled={deleteJobMutation.isPending}>
                <Trash2 className="h-4 w-4 mr-2" />
                {t('delete')}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>{t('deleteConfirmTitle')}</AlertDialogTitle>
                <AlertDialogDescription>
                  {t('deleteConfirmMessage')}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
                <AlertDialogAction onClick={handleDeleteJob}>
                  {t('delete')}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </div>

      {/* Status Card */}
      <JobStatusCard
        status={currentStatus}
        progress={currentProgress}
        isConnected={isConnected}
        duration={duration}
      />

      {/* Token Metrics Card - shown when metrics available */}
      {currentTokenMetrics && (
        <JobMetricsCard
          metrics={currentTokenMetrics}
          isLive={isActiveJob && isConnected}
        />
      )}

      {/* Unified Processing Timeline - always shown for completed jobs */}
      {currentStatus === 'completed' && (
        <JobProcessingTimeline
          metrics={job?.token_metrics || null}
          processingMode={job?.processing_mode || 'iterative'}
          currentPassNumber={currentPassMetrics?.pass_number}
          isLive={isActiveJob}
        />
      )}

      {/* Edit mode or result view */}
      {isEditing ? (
        <JobResultEditor
          jobId={id}
          initialContent={extractedContent}
          outputType={job?.output_type || 'text'}
          onSave={handleSaveEdit}
          onCancel={() => setIsEditing(false)}
        />
      ) : (
        <JobResultView
          result={currentResult}
          error={currentError}
          status={currentStatus}
          outputType={job?.output_type}
          onEdit={currentStatus === 'completed' ? () => setIsEditing(true) : undefined}
          onShowHistory={currentStatus === 'completed' ? () => setIsHistoryOpen(true) : undefined}
          currentVersion={job?.current_version}
          lastEditedAt={job?.last_edited_at}
          jobId={id}
          jobServiceName={job?.service_name}
        />
      )}

      {/* Re-extract Metadata Button - only show if flavor has extraction prompt */}
      {currentStatus === 'completed' && job?.has_extraction_prompt && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            onClick={() => extractMetadataMutation.mutate({ jobId: id })}
            disabled={extractMetadataMutation.isPending}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${extractMetadataMutation.isPending ? 'animate-spin' : ''}`} />
            {extractMetadataMutation.isPending ? t('extractingMetadata') : t('reExtractMetadata')}
          </Button>
        </div>
      )}

      {/* Extracted Metadata Display */}
      {job?.result?.extracted_metadata && Object.keys(job.result.extracted_metadata).length > 0 && (
        <MetadataDisplay
          metadata={job.result.extracted_metadata}
        />
      )}

      {/* Categorization Display */}
      {job?.result?.categorization && (
        <CategorizationDisplay categorization={job.result.categorization} />
      )}

      {/* Version history dialog */}
      {isHistoryOpen && job && (
        <JobVersionHistory
          jobId={id}
          currentVersion={job.current_version ?? 1}
          onRestore={handleRestoreVersion}
          onClose={() => setIsHistoryOpen(false)}
        />
      )}

      {/* Metadata Card */}
      <JobMetadata job={job} />
    </div>
  );
}
