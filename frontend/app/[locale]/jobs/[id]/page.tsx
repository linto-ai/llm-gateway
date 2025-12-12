'use client';

import { use, useMemo, useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Trash2 } from 'lucide-react';
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
  MetadataDisplay,
  CategorizationDisplay,
} from '@/components/jobs';

import { useJob, useDeleteJob } from '@/hooks/use-jobs';
import { useJobWebSocket } from '@/hooks/use-job-websocket';
import { useUpdateJobResult, useJobVersion } from '@/hooks/use-job-versions';
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

  // Edit state
  const [isEditing, setIsEditing] = useState(false);

  // Version viewing state - null means viewing current version
  const [viewingVersionNumber, setViewingVersionNumber] = useState<number | null>(null);

  // Fetch specific version content when viewing a non-current version
  const {
    data: versionData,
    isLoading: isLoadingVersion,
  } = useJobVersion(id, viewingVersionNumber ?? 0);

  // Mutations for editing and deleting
  const updateResultMutation = useUpdateJobResult(id);
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

  // Extract content from result for editing (always from current version, not viewed version)
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
      // Reset to viewing current version after save
      setViewingVersionNumber(null);
      toast.success(t('editor.saveSuccess'));
    } catch (error: any) {
      toast.error(error.message || t('editor.saveError'));
      throw error; // Re-throw so editor knows save failed
    }
  }, [updateResultMutation, t]);

  // Handle version change - just switch the viewing version
  const handleVersionChange = useCallback((versionNumber: number) => {
    const currentVer = job?.current_version ?? 1;
    // If selecting current version, clear the viewing state
    if (versionNumber === currentVer) {
      setViewingVersionNumber(null);
    } else {
      setViewingVersionNumber(versionNumber);
    }
  }, [job?.current_version]);

  // Determine which content to display based on viewing version
  const displayResult = useMemo(() => {
    // If viewing a specific version (not current), use version data
    if (viewingVersionNumber !== null && versionData?.content) {
      // Wrap in same format as job result
      return { output: versionData.content };
    }
    // Otherwise use current result
    return currentResult;
  }, [viewingVersionNumber, versionData, currentResult]);

  // Determine which metadata to display based on viewing version
  const displayMetadata = useMemo(() => {
    // If viewing a non-current version
    if (viewingVersionNumber !== null) {
      // Version 1 uses the main extracted_metadata (that's where it was originally extracted from)
      if (viewingVersionNumber === 1) {
        return job?.result?.extracted_metadata ?? null;
      }
      // Other versions: check version_extractions cache
      const versionExtractions = job?.result?.version_extractions;
      if (versionExtractions) {
        const versionKey = String(viewingVersionNumber);
        const versionExtraction = versionExtractions[versionKey];
        if (versionExtraction?.metadata) {
          return versionExtraction.metadata;
        }
      }
      // No cached metadata for this version - show nothing
      return null;
    }
    // Viewing current version - use main extracted_metadata
    return job?.result?.extracted_metadata ?? null;
  }, [viewingVersionNumber, job?.result]);

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
          result={displayResult}
          error={currentError}
          status={currentStatus}
          outputType={job?.output_type}
          onEdit={currentStatus === 'completed' && viewingVersionNumber === null ? () => setIsEditing(true) : undefined}
          currentVersion={job?.current_version}
          viewingVersion={viewingVersionNumber ?? job?.current_version}
          onVersionChange={currentStatus === 'completed' ? handleVersionChange : undefined}
          isLoadingVersion={isLoadingVersion}
          lastEditedAt={job?.last_edited_at}
          jobId={id}
          jobServiceName={job?.service_name}
        />
      )}

      {/* Extracted Metadata Display */}
      {displayMetadata && Object.keys(displayMetadata).length > 0 && (
        <MetadataDisplay
          metadata={displayMetadata}
        />
      )}

      {/* Categorization Display */}
      {job?.result?.categorization && (
        <CategorizationDisplay categorization={job.result.categorization} />
      )}

      {/* Metadata Card */}
      <JobMetadata job={job} />
    </div>
  );
}
