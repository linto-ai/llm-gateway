'use client';

import { useState, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import dynamic from 'next/dynamic';
import { Copy, Check, Download, AlertCircle, FileText, Code, Pencil, FileOutput, Loader2, Info } from 'lucide-react';
import { toast } from 'sonner';
import remarkGfm from 'remark-gfm';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useExportJob } from '@/hooks/use-document-templates';
import { VersionDropdown } from './VersionDropdown';
import type { ExportFormat } from '@/types/document-template';

// Lazy load ReactMarkdown for performance with large results
const ReactMarkdown = dynamic(() => import('react-markdown'), {
  loading: () => <div className="animate-pulse text-muted-foreground">Loading markdown renderer...</div>,
});

// Size threshold for defaulting to raw view (100KB)
const LARGE_RESULT_THRESHOLD = 100 * 1024;

interface JobResultViewProps {
  result: any | null;
  error: string | null;
  status: 'completed' | 'failed' | string;
  // Output type from flavor configuration
  outputType?: 'text' | 'markdown' | 'json';
  // Edit callback
  onEdit?: () => void;
  // Version viewing
  currentVersion?: number;
  viewingVersion?: number;
  onVersionChange?: (version: number) => void;
  isLoadingVersion?: boolean;
  lastEditedAt?: string | null;
  // Export functionality
  jobId?: string;
  jobServiceName?: string;
}

export function JobResultView({
  result,
  error,
  status,
  outputType = 'text',
  onEdit,
  currentVersion = 1,
  viewingVersion,
  onVersionChange,
  isLoadingVersion = false,
  lastEditedAt,
  jobId,
  jobServiceName,
}: JobResultViewProps) {
  const t = useTranslations('jobs');
  const [copied, setCopied] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Export mutation
  const exportMutation = useExportJob();

  // Handle export - uses the currently viewed version
  const handleExport = async (format: ExportFormat) => {
    if (!jobId) return;

    setIsExporting(true);
    try {
      const versionToExport = viewingVersion ?? currentVersion;
      const fileName = `${jobServiceName || 'job'}-${jobId.slice(0, 8)}-v${versionToExport}.${format}`;
      await exportMutation.mutateAsync({
        jobId,
        format,
        versionNumber: versionToExport,
        fileName,
      });
      toast.success(t('export.success'));
    } catch (error: any) {
      toast.error(error.message || t('export.error'));
    } finally {
      setIsExporting(false);
    }
  };

  // Extract the actual content from the result
  // Backend wraps result as {"output": "..."}
  const extractedContent = useMemo(() => {
    if (!result) return null;
    if (typeof result === 'string') return result;
    if (typeof result === 'object' && result.output) {
      return result.output;
    }
    return JSON.stringify(result, null, 2);
  }, [result]);

  // Use outputType prop instead of regex detection
  const shouldRenderMarkdown = outputType === 'markdown';

  // Check if content is large for lazy rendering
  const isLargeResult = useMemo(() => {
    if (!extractedContent) return false;
    return extractedContent.length > LARGE_RESULT_THRESHOLD;
  }, [extractedContent]);

  // For large markdown results, default to raw tab
  const defaultTab = shouldRenderMarkdown && isLargeResult ? 'raw' : 'rendered';

  const formattedResult =
    typeof result === 'string' ? result : JSON.stringify(result, null, 2);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(formattedResult);
      setCopied(true);
      toast.success(t('copySuccess'));
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(t('copyError'));
    }
  };

  const downloadResult = () => {
    try {
      const isJson = typeof result !== 'string';
      const blob = new Blob([formattedResult], {
        type: isJson ? 'application/json' : 'text/plain',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `job-result.${isJson ? 'json' : 'txt'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success(t('downloadSuccess'));
    } catch {
      toast.error(t('downloadError'));
    }
  };

  // Show error view for failed jobs
  if (status === 'failed' && error) {
    return (
      <Card className="border-destructive">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg text-destructive flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            {t('error')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-destructive/10 text-destructive rounded-md p-4">
            <p className="font-medium">{t('failed')}</p>
            <p className="text-sm mt-2 font-mono">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show result view for completed jobs
  if (status === 'completed') {
    return (
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg">{t('result')}</CardTitle>
              {/* Version dropdown - only show if we have jobId and version change capability */}
              {jobId && onVersionChange && (
                <VersionDropdown
                  jobId={jobId}
                  viewingVersion={viewingVersion ?? currentVersion}
                  currentVersion={currentVersion}
                  onVersionChange={onVersionChange}
                  isLoading={isLoadingVersion}
                />
              )}
            </div>
            {result && (
              <div className="flex items-center gap-2">
                {/* Edit button */}
                {onEdit && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onEdit}
                    className="h-8"
                  >
                    <Pencil className="h-4 w-4 mr-1" />
                    {t('editor.editButton')}
                  </Button>
                )}
                {/* Export buttons */}
                {jobId && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8"
                        disabled={isExporting}
                      >
                        {isExporting ? (
                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                        ) : (
                          <FileOutput className="h-4 w-4 mr-1" />
                        )}
                        {isExporting ? t('export.progress') : 'Export'}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleExport('docx')}>
                        <FileText className="h-4 w-4 mr-2" />
                        {t('export.docx')}
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleExport('pdf')}>
                        <FileText className="h-4 w-4 mr-2" />
                        {t('export.pdf')}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={copyToClipboard}
                  className="h-8"
                >
                  {copied ? (
                    <Check className="h-4 w-4 mr-1 text-green-500" />
                  ) : (
                    <Copy className="h-4 w-4 mr-1" />
                  )}
                  {t('copyResult')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={downloadResult}
                  className="h-8"
                >
                  <Download className="h-4 w-4 mr-1" />
                  {t('downloadResult')}
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Info banner when viewing an old version */}
          {viewingVersion && viewingVersion !== currentVersion && (
            <Alert className="mb-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <AlertDescription className="text-blue-700 dark:text-blue-300">
                {t('versions.viewingOldVersion', { number: viewingVersion })}
              </AlertDescription>
            </Alert>
          )}
          {extractedContent ? (
            shouldRenderMarkdown ? (
              <Tabs defaultValue={defaultTab} className="w-full">
                <TabsList className="mb-4">
                  <TabsTrigger value="rendered" className="gap-2">
                    <FileText className="h-4 w-4" />
                    {t('renderedView')}
                  </TabsTrigger>
                  <TabsTrigger value="raw" className="gap-2">
                    <Code className="h-4 w-4" />
                    {t('rawView')}
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="rendered">
                  <div className="prose prose-sm dark:prose-invert max-w-none bg-muted/50 p-4 rounded-md overflow-auto max-h-[600px]">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {extractedContent}
                    </ReactMarkdown>
                  </div>
                </TabsContent>
                <TabsContent value="raw">
                  <pre className="text-sm bg-muted p-4 rounded-md overflow-auto max-h-[500px] font-mono whitespace-pre-wrap">
                    {extractedContent}
                  </pre>
                </TabsContent>
              </Tabs>
            ) : (
              <pre className="text-sm bg-muted p-4 rounded-md overflow-auto max-h-[500px] font-mono whitespace-pre-wrap">
                {extractedContent}
              </pre>
            )
          ) : (
            <p className="text-sm text-muted-foreground">{t('noResult')}</p>
          )}
        </CardContent>
      </Card>
    );
  }

  // For other statuses, show waiting message
  return null;
}
