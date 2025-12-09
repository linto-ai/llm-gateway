'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { formatDistanceToNow } from 'date-fns';
import dynamic from 'next/dynamic';
import remarkGfm from 'remark-gfm';
import { History, RotateCcw, Eye, EyeOff, Clock, FileText, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';

import { useJobVersions, useJobVersion } from '@/hooks/use-job-versions';
import type { JobVersionSummary } from '@/types/job';

// Lazy load ReactMarkdown
const ReactMarkdown = dynamic(() => import('react-markdown'), {
  loading: () => <div className="animate-pulse text-muted-foreground">Loading...</div>,
});

interface JobVersionHistoryProps {
  jobId: string;
  currentVersion: number;
  onRestore: (version: number) => Promise<void>;
  onClose: () => void;
}

export function JobVersionHistory({
  jobId,
  currentVersion,
  onRestore,
  onClose,
}: JobVersionHistoryProps) {
  const t = useTranslations('jobs');

  // Fetch version list
  const { data: versions, isLoading: isLoadingVersions, error } = useJobVersions(jobId);

  // State for viewing version content
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [restoreVersion, setRestoreVersion] = useState<number | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);

  // Fetch selected version content
  const { data: versionContent, isLoading: isLoadingContent } = useJobVersion(
    jobId,
    selectedVersion ?? 0
  );

  // Handle restore confirmation
  const handleRestoreConfirm = async () => {
    if (restoreVersion === null) return;

    setIsRestoring(true);
    try {
      await onRestore(restoreVersion);
      setRestoreVersion(null);
      onClose();
    } finally {
      setIsRestoring(false);
    }
  };

  // Toggle version content preview
  const toggleVersionPreview = (versionNumber: number) => {
    setSelectedVersion((prev) => (prev === versionNumber ? null : versionNumber));
  };

  // Format content length
  const formatContentLength = (length: number): string => {
    if (length < 1000) return `${length} chars`;
    if (length < 1000000) return `${(length / 1000).toFixed(1)}k chars`;
    return `${(length / 1000000).toFixed(1)}M chars`;
  };

  return (
    <Dialog open={true} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            {t('versions.title')}
          </DialogTitle>
          <DialogDescription>
            {t('versions.description', { version: currentVersion })}
          </DialogDescription>
        </DialogHeader>

        {/* Version list */}
        <ScrollArea className="flex-1 pr-4">
          {isLoadingVersions ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3 p-3 border rounded-lg">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="text-center py-8 text-destructive">
              {t('versions.loadError')}
            </div>
          ) : !versions || versions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {t('versions.noVersions')}
            </div>
          ) : (
            <div className="space-y-2">
              {versions.map((version) => (
                <VersionItem
                  key={version.version_number}
                  version={version}
                  isCurrent={version.version_number === currentVersion}
                  isOriginal={version.version_number === 1}
                  isExpanded={selectedVersion === version.version_number}
                  expandedContent={
                    selectedVersion === version.version_number ? versionContent?.content : undefined
                  }
                  isLoadingContent={
                    selectedVersion === version.version_number && isLoadingContent
                  }
                  onTogglePreview={() => toggleVersionPreview(version.version_number)}
                  onRestore={() => setRestoreVersion(version.version_number)}
                  canRestore={version.version_number !== currentVersion}
                  formatContentLength={formatContentLength}
                  t={t}
                />
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Restore confirmation dialog */}
        <AlertDialog open={restoreVersion !== null} onOpenChange={() => setRestoreVersion(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t('versions.restoreTitle')}</AlertDialogTitle>
              <AlertDialogDescription>
                {t('versions.restoreConfirm', { number: restoreVersion ?? 0 })}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isRestoring}>
                {t('editor.cancel')}
              </AlertDialogCancel>
              <AlertDialogAction onClick={handleRestoreConfirm} disabled={isRestoring}>
                {isRestoring ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {t('versions.restoring')}
                  </>
                ) : (
                  t('versions.restore')
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </DialogContent>
    </Dialog>
  );
}

// Individual version item component
interface VersionItemProps {
  version: JobVersionSummary;
  isCurrent: boolean;
  isOriginal: boolean;
  isExpanded: boolean;
  expandedContent?: string;
  isLoadingContent: boolean;
  onTogglePreview: () => void;
  onRestore: () => void;
  canRestore: boolean;
  formatContentLength: (length: number) => string;
  t: ReturnType<typeof useTranslations<'jobs'>>;
}

function VersionItem({
  version,
  isCurrent,
  isOriginal,
  isExpanded,
  expandedContent,
  isLoadingContent,
  onTogglePreview,
  onRestore,
  canRestore,
  formatContentLength,
  t,
}: VersionItemProps) {
  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Version header */}
      <div className="flex items-center justify-between p-3 bg-muted/30">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
            {version.version_number}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">
                {t('versions.version', { number: version.version_number })}
              </span>
              {isCurrent && (
                <Badge variant="default" className="text-xs">
                  {t('versions.current')}
                </Badge>
              )}
              {isOriginal && (
                <Badge variant="secondary" className="text-xs">
                  {t('versions.original')}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-3 w-3" />
              {formatDistanceToNow(new Date(version.created_at), { addSuffix: true })}
              <span className="text-muted-foreground/50">|</span>
              <FileText className="h-3 w-3" />
              {formatContentLength(version.content_length)}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onTogglePreview}
            className="h-8"
          >
            {isExpanded ? (
              <>
                <EyeOff className="h-4 w-4 mr-1" />
                {t('versions.hideContent')}
              </>
            ) : (
              <>
                <Eye className="h-4 w-4 mr-1" />
                {t('versions.viewContent')}
              </>
            )}
          </Button>
          {canRestore && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRestore}
              className="h-8"
            >
              <RotateCcw className="h-4 w-4 mr-1" />
              {t('versions.restore')}
            </Button>
          )}
        </div>
      </div>

      {/* Expanded content preview */}
      {isExpanded && (
        <>
          <Separator />
          <div className="p-3 bg-background">
            {isLoadingContent ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : expandedContent ? (
              <div className="prose prose-sm dark:prose-invert max-w-none bg-muted/30 p-3 rounded-md overflow-auto max-h-[300px]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {expandedContent}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                {t('versions.contentUnavailable')}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
