'use client';

import { useTranslations } from 'next-intl';
import { AlertTriangle, CheckCircle2, Clock, Loader2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';

import { useExportPreview } from '@/hooks/use-document-templates';
import type { PlaceholderStatus } from '@/types/document-template';

interface ExportPreviewCardProps {
  jobId: string;
  templateId?: string;
}

/**
 * Preview component showing placeholder status before export.
 * Displays which placeholders are available, missing, or require extraction.
 */
export function ExportPreviewCard({ jobId, templateId }: ExportPreviewCardProps) {
  const t = useTranslations('jobs.export');

  const { data: preview, isLoading, error } = useExportPreview(jobId, templateId);

  // Get badge variant based on status
  const getStatusBadgeVariant = (
    status: PlaceholderStatus['status']
  ): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (status) {
      case 'available':
        return 'default';
      case 'extraction_required':
        return 'secondary';
      case 'missing':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  // Get status icon
  const getStatusIcon = (status: PlaceholderStatus['status']) => {
    switch (status) {
      case 'available':
        return <CheckCircle2 className="h-3 w-3" />;
      case 'extraction_required':
        return <Clock className="h-3 w-3" />;
      case 'missing':
        return <AlertTriangle className="h-3 w-3" />;
      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-4 w-24" />
        <div className="flex flex-wrap gap-2">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-6 w-20" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !preview) {
    return null; // Silently fail - preview is optional
  }

  // Group placeholders by status
  const availablePlaceholders = preview.placeholders.filter(
    (p) => p.status === 'available'
  );
  const extractionRequiredPlaceholders = preview.placeholders.filter(
    (p) => p.status === 'extraction_required'
  );
  const missingPlaceholders = preview.placeholders.filter(
    (p) => p.status === 'missing'
  );

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-medium mb-2">{t('preview')}</h4>
        <p className="text-xs text-muted-foreground mb-3">
          {t('previewDescription', { template: preview.template_name })}
        </p>
      </div>

      {/* Placeholder list */}
      <div className="flex flex-wrap gap-2">
        {preview.placeholders.map((p) => (
          <Badge
            key={p.name}
            variant={getStatusBadgeVariant(p.status)}
            className="gap-1 font-mono text-xs"
            title={p.value ? `${t(`placeholderStatus.${p.status}`)}: ${p.value}` : t(`placeholderStatus.${p.status}`)}
          >
            {getStatusIcon(p.status)}
            {`{{${p.name}}}`}
          </Badge>
        ))}
      </div>

      {/* Extraction warning */}
      {preview.extraction_required && (
        <Alert variant="default" className="bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-800">
          <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
          <AlertDescription className="text-yellow-800 dark:text-yellow-200">
            {t('extractionRequired', {
              tokens: preview.estimated_extraction_tokens || '~',
            })}
          </AlertDescription>
        </Alert>
      )}

      {/* Missing placeholders warning */}
      {missingPlaceholders.length > 0 && !preview.extraction_required && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {t('missingPlaceholders', {
              count: missingPlaceholders.length,
              placeholders: missingPlaceholders.map((p) => p.name).join(', '),
            })}
          </AlertDescription>
        </Alert>
      )}

      {/* Status summary */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        {availablePlaceholders.length > 0 && (
          <span className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3 text-green-500" />
            {t('statusSummary.available', { count: availablePlaceholders.length })}
          </span>
        )}
        {extractionRequiredPlaceholders.length > 0 && (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3 text-yellow-500" />
            {t('statusSummary.extraction', { count: extractionRequiredPlaceholders.length })}
          </span>
        )}
        {missingPlaceholders.length > 0 && (
          <span className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3 text-red-500" />
            {t('statusSummary.missing', { count: missingPlaceholders.length })}
          </span>
        )}
      </div>
    </div>
  );
}
