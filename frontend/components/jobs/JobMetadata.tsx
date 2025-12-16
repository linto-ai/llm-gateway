'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { format, formatDistanceToNow } from 'date-fns';
import { Copy, Check, FileText, AlertTriangle, Clock } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { isExpired, isExpiringSoon } from '@/lib/utils';
import type { JobResponse } from '@/types/job';

interface JobMetadataProps {
  job: JobResponse;
}

export function JobMetadata({ job }: JobMetadataProps) {
  const t = useTranslations('jobs');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      toast.success(t('copySuccess'));
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      toast.error(t('copyError'));
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return format(new Date(dateString), 'PPpp');
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5" />
          {t('metadata')}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Job ID */}
          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">{t('jobId')}</span>
            <div className="flex items-center gap-2">
              <code className="text-xs bg-muted px-2 py-1 rounded font-mono break-all">
                {job.id}
              </code>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 flex-shrink-0"
                onClick={() => copyToClipboard(job.id, 'id')}
              >
                {copiedField === 'id' ? (
                  <Check className="h-3 w-3 text-green-500" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </Button>
            </div>
          </div>

          {/* Service Name */}
          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">{t('serviceName')}</span>
            <p className="font-medium">{job.service_name}</p>
          </div>

          {/* Flavor Name */}
          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">{t('flavorName')}</span>
            <p className="font-medium">{job.flavor_name}</p>
          </div>

          {/* Created At */}
          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">{t('createdAt')}</span>
            <p>{formatDate(job.created_at)}</p>
          </div>

          {/* Started At */}
          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">{t('startedAt')}</span>
            <p>{formatDate(job.started_at)}</p>
          </div>

          {/* Completed At */}
          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">{t('completedAt')}</span>
            <p>{formatDate(job.completed_at)}</p>
          </div>

          {/* Expires At */}
          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">{t('expiresAt')}</span>
            <div className="flex items-center gap-2">
              {job.expires_at === null ? (
                <p className="text-muted-foreground">{t('expiration.never')}</p>
              ) : isExpired(job.expires_at) ? (
                <>
                  <p className="line-through">{formatDate(job.expires_at)}</p>
                  <Badge variant="destructive" className="text-xs">
                    {t('expiration.expired')}
                  </Badge>
                </>
              ) : isExpiringSoon(job.expires_at) ? (
                <>
                  <p>{formatDate(job.expires_at)}</p>
                  <Badge variant="outline" className="text-xs text-yellow-600 border-yellow-400">
                    <Clock className="h-3 w-3 mr-1" />
                    {t('expiration.expiringSoon')}
                  </Badge>
                </>
              ) : (
                <p>{formatDate(job.expires_at)}</p>
              )}
            </div>
          </div>

          {/* Organization ID (if present) */}
          {job.organization_id && (
            <div className="space-y-1">
              <span className="text-sm text-muted-foreground">{t('organizationId')}</span>
              <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                {job.organization_id}
              </code>
            </div>
          )}

          {/* Fallback Applied Info */}
          {job.fallback_applied && (
            <>
              <div className="space-y-1 col-span-full border-t pt-4 mt-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-500" />
                  <span className="text-sm font-medium text-yellow-700 dark:text-yellow-400">
                    {t('fallbackApplied')}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {t('fallbackBadge')}
                  </Badge>
                </div>
              </div>

              {/* Original Flavor */}
              {job.original_flavor_name && (
                <div className="space-y-1">
                  <span className="text-sm text-muted-foreground">{t('originalFlavor')}</span>
                  <p className="font-medium">{job.original_flavor_name}</p>
                </div>
              )}

              {/* Input Tokens */}
              {job.input_tokens !== undefined && job.input_tokens !== null && (
                <div className="space-y-1">
                  <span className="text-sm text-muted-foreground">{t('inputTokens')}</span>
                  <p className="font-medium">{job.input_tokens.toLocaleString()}</p>
                </div>
              )}

              {/* Context Available */}
              {job.context_available !== undefined && job.context_available !== null && (
                <div className="space-y-1">
                  <span className="text-sm text-muted-foreground">{t('contextAvailable')}</span>
                  <p className="font-medium">{job.context_available.toLocaleString()}</p>
                </div>
              )}

              {/* Fallback Reason */}
              {job.fallback_reason && (
                <div className="space-y-1 col-span-full">
                  <span className="text-sm text-muted-foreground">{t('fallbackReason')}</span>
                  <p className="text-sm">{job.fallback_reason}</p>
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
