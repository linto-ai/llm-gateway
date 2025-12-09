'use client';

import { useState, useEffect } from 'react';
import { Loader2, FolderOpen, AlertTriangle, CheckCircle2, Info, Zap, Wifi, WifiOff } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import { FileUpload } from './FileUpload';
import { JobResult } from './JobResult';
import { SyntheticTemplateBrowser } from './SyntheticTemplateBrowser';
import { useExecuteService, useJob } from '@/hooks/use-jobs';
import { useJobWebSocket } from '@/hooks/use-job-websocket';
import { useValidateExecution } from '@/hooks/use-services';
import type { ServiceResponse, ExecuteServiceResponse, ExecutionErrorCode, ExecutionValidationResponse } from '@/types/service';
import type { JobStatus } from '@/types/job';

interface ServiceExecutionFormProps {
  service: ServiceResponse;
}

// Fallback info state
interface FallbackInfo {
  applied: boolean;
  originalFlavorName?: string;
  fallbackFlavorName?: string;
  reason?: string;
  inputTokens?: number;
  contextAvailable?: number;
}

export function ServiceExecutionForm({ service }: ServiceExecutionFormProps) {
  const t = useTranslations();
  const [file, setFile] = useState<File | null>(null);
  const [selectedFlavorId, setSelectedFlavorId] = useState<string>('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [templateBrowserOpen, setTemplateBrowserOpen] = useState(false);
  const [selectedTemplateName, setSelectedTemplateName] = useState<string | null>(null);
  // Track fallback info from execution response
  const [fallbackInfo, setFallbackInfo] = useState<FallbackInfo | null>(null);
  // Dry run validation state
  const [validationResult, setValidationResult] = useState<ExecutionValidationResponse | null>(null);

  const executeMutation = useExecuteService();
  const validateMutation = useValidateExecution();

  // Helper to check if status is terminal
  const isTerminalState = (status: JobStatus | undefined | null) =>
    status ? ['completed', 'failed', 'cancelled'].includes(status) : false;

  // WebSocket for real-time progress during job execution
  // Declare this FIRST so we can use wsConnected in the polling logic
  const {
    status: wsStatus,
    progress: wsProgress,
    result: wsResult,
    error: wsError,
    isConnected: wsConnected,
  } = useJobWebSocket(jobId ?? '', {
    enabled: !!jobId,
  });

  // Poll job status ONLY as fallback when WebSocket is NOT connected
  // WebSocket provides real-time updates, polling is redundant when WS works
  const { data: jobStatus, isLoading: isPolling } = useJob(jobId, {
    refetchInterval: (data) => {
      // Stop polling if terminal state (from REST or WebSocket)
      if (isTerminalState(data?.status) || isTerminalState(wsStatus)) {
        return false;
      }
      // If WebSocket is connected, NO polling needed - WS handles updates
      if (wsConnected) {
        return false;
      }
      // WebSocket not connected - use polling as fallback
      return 2000;
    },
  });

  // Merge WebSocket updates with REST data (WebSocket takes priority)
  const currentStatus = wsStatus || jobStatus?.status;
  const currentProgress = wsProgress || jobStatus?.progress || null;
  const currentResult = wsResult !== null ? wsResult : jobStatus?.result;
  const currentError = wsError || jobStatus?.error || null;

  const isExecuting = executeMutation.isPending;
  const isValidating = validateMutation.isPending;
  // Use merged status for isJobRunning check
  const isJobRunning = Boolean(
    currentStatus && ['queued', 'started', 'processing'].includes(currentStatus)
  );

  const handleTemplateSelect = (filename: string, content: string) => {
    // Convert content to File object for compatibility with existing execution flow
    const blob = new Blob([content], { type: 'text/plain' });
    const templateFile = new File([blob], filename, { type: 'text/plain' });
    setFile(templateFile);
    setSelectedTemplateName(filename);
    setTemplateBrowserOpen(false);
    setValidationResult(null); // Clear validation when file changes
  };

  // Set default flavor on mount
  useEffect(() => {
    if (service.flavors.length > 0 && !selectedFlavorId) {
      const defaultFlavor = service.flavors.find(f => f.is_default) || service.flavors[0];
      setSelectedFlavorId(defaultFlavor.id);
    }
  }, [service.flavors, selectedFlavorId]);

  // Helper to get user-friendly error message based on error code
  const getExecutionErrorMessage = (error: any): string => {
    const errorCode = error?.error_code as ExecutionErrorCode | undefined;
    const inputTokens = error?.input_tokens;
    const availableTokens = error?.available_tokens;

    switch (errorCode) {
      case 'CONTEXT_EXCEEDED':
        return t('services.execution.errors.contextExceeded', {
          inputTokens: inputTokens ?? '?',
          availableTokens: availableTokens ?? '?',
        });
      case 'CONTEXT_EXCEEDED_NO_FALLBACK':
        return t('services.execution.errors.contextExceededNoFallback');
      case 'FLAVOR_INACTIVE':
        return t('services.execution.errors.flavorInactive');
      case 'FALLBACK_FLAVOR_INACTIVE':
        return t('services.execution.errors.fallbackFlavorInactive');
      default:
        return error?.message || error?.detail || t('services.execution.errors.executionFailed');
    }
  };

  // Dry run validation handler
  const handleDryRun = async () => {
    if (!file || !selectedFlavorId) {
      toast.error(t('services.execution.errors.missingFields'));
      return;
    }

    const formData = new FormData();
    formData.append('flavor_id', selectedFlavorId);
    formData.append('file', file);

    try {
      const result = await validateMutation.mutateAsync({
        serviceId: service.id,
        formData,
      });
      setValidationResult(result);
    } catch (error: any) {
      toast.error(error?.message || t('services.execution.dryRun.error'));
    }
  };

  const handleExecute = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file || !selectedFlavorId) {
      toast.error(t('services.execution.errors.missingFields'));
      return;
    }

    // Reset fallback info and validation on new execution
    setFallbackInfo(null);
    setValidationResult(null);

    try {
      const response = await executeMutation.mutateAsync({
        serviceId: service.id,
        flavorId: selectedFlavorId,
        file,
      });

      setJobId(response.job_id);

      // Handle fallback applied scenario
      if (response.fallback_applied) {
        setFallbackInfo({
          applied: true,
          originalFlavorName: response.original_flavor_name,
          fallbackFlavorName: response.flavor_name,
          reason: response.fallback_reason,
          inputTokens: response.input_tokens,
          contextAvailable: response.context_available,
        });
        toast.warning(t('services.execution.fallbackApplied'), {
          description: t('services.execution.fallbackDetails', {
            original: response.original_flavor_name || '?',
            fallback: response.flavor_name || '?',
          }),
          duration: 6000,
        });
      } else {
        toast.success(t('services.execution.success'));
      }
    } catch (error: any) {
      const errorMessage = getExecutionErrorMessage(error);
      toast.error(errorMessage);
    }
  };

  // Get selected flavor details
  const selectedFlavor = service.flavors.find(f => f.id === selectedFlavorId);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{t('services.execution.title')}</CardTitle>
          <CardDescription>{t('services.execution.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleExecute} className="space-y-6">
            {/* File Upload */}
            <div className="space-y-2">
              <Label htmlFor="file">{t('services.execution.file')}</Label>
              <FileUpload
                onFileSelect={(f) => {
                  setFile(f);
                  setSelectedTemplateName(null); // Clear template name when user uploads
                  setValidationResult(null); // Clear validation when file changes
                }}
                disabled={isExecuting || isJobRunning || isValidating}
              />
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setTemplateBrowserOpen(true)}
                  disabled={isExecuting || isJobRunning || isValidating}
                >
                  <FolderOpen className="mr-2 h-4 w-4" />
                  {t('services.execution.browseSyntheticTemplates')}
                </Button>
                {selectedTemplateName && (
                  <span className="text-sm text-muted-foreground">
                    {t('services.execution.syntheticTemplate')}: {selectedTemplateName}
                  </span>
                )}
              </div>
            </div>

            {/* Flavor Selector */}
            <div className="space-y-2">
              <Label htmlFor="flavor">{t('services.execution.flavor')}</Label>
              <Select
                value={selectedFlavorId}
                onValueChange={(v) => {
                  setSelectedFlavorId(v);
                  setValidationResult(null); // Clear validation when flavor changes
                }}
                disabled={isExecuting || isJobRunning || isValidating}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t('services.execution.selectFlavor')} />
                </SelectTrigger>
                <SelectContent>
                  {service.flavors.map((flavor) => (
                    <SelectItem key={flavor.id} value={flavor.id}>
                      <div className="flex items-center gap-2">
                        <span>
                          {flavor.name}{flavor.is_default ? ` (${t('services.flavors.default')})` : ''}
                        </span>
                        <span className="text-muted-foreground text-xs">
                          - T: {flavor.temperature}, {flavor.model?.model_name || '-'}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedFlavor && (
                <p className="text-xs text-muted-foreground">
                  {t('services.execution.flavorInfoUpdated', {
                    temperature: selectedFlavor.temperature,
                    topP: selectedFlavor.top_p,
                    model: selectedFlavor.model?.model_name || '-',
                  })}
                </p>
              )}
            </div>

            {/* Validation Result Display */}
            {validationResult && (
              <Alert
                variant={validationResult.valid ? 'default' : 'destructive'}
                className={validationResult.valid
                  ? validationResult.warning
                    ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950'
                    : 'border-green-500 bg-green-50 dark:bg-green-950'
                  : 'border-red-500 bg-red-50 dark:bg-red-950'
                }
              >
                {validationResult.valid ? (
                  validationResult.warning ? (
                    <Info className="h-4 w-4 text-yellow-600" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  )
                ) : (
                  <Info className="h-4 w-4 text-red-600" />
                )}
                <AlertTitle className={validationResult.valid
                  ? validationResult.warning
                    ? 'text-yellow-800 dark:text-yellow-200'
                    : 'text-green-800 dark:text-green-200'
                  : 'text-red-800 dark:text-red-200'
                }>
                  {validationResult.valid
                    ? validationResult.warning
                      ? t('services.execution.dryRun.validWithWarning')
                      : t('services.execution.dryRun.validTitle')
                    : t('services.execution.dryRun.invalidTitle')
                  }
                </AlertTitle>
                <AlertDescription className={validationResult.valid
                  ? validationResult.warning
                    ? 'text-yellow-700 dark:text-yellow-300'
                    : 'text-green-700 dark:text-green-300'
                  : 'text-red-700 dark:text-red-300'
                }>
                  {validationResult.warning && (
                    <p className="mb-2">{validationResult.warning}</p>
                  )}
                  {(validationResult.input_tokens || validationResult.estimated_cost) && (
                    <div className="flex flex-wrap gap-2 text-sm">
                      {validationResult.input_tokens && (
                        <Badge variant="outline">
                          {validationResult.input_tokens.toLocaleString()} tokens
                        </Badge>
                      )}
                      {validationResult.max_generation && (
                        <Badge variant="outline" className="text-muted-foreground">
                          + {validationResult.max_generation.toLocaleString()} max gen
                        </Badge>
                      )}
                      {validationResult.estimated_cost && (
                        <Badge variant="secondary">
                          ~${validationResult.estimated_cost.toFixed(4)}
                        </Badge>
                      )}
                    </div>
                  )}
                </AlertDescription>
              </Alert>
            )}

            {/* WebSocket Connection Status during execution */}
            {jobId && isJobRunning && (
              <div className="flex items-center text-xs">
                {wsConnected ? (
                  <span className="text-green-600 flex items-center">
                    <Wifi className="h-3 w-3 mr-1" />
                    {t('jobs.websocketConnected')}
                  </span>
                ) : (
                  <span className="text-muted-foreground flex items-center">
                    <WifiOff className="h-3 w-3 mr-1" />
                    {t('jobs.websocketDisconnected')}
                  </span>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2">
              {/* Dry Run Button */}
              <Button
                type="button"
                variant="outline"
                onClick={handleDryRun}
                disabled={!file || !selectedFlavorId || isExecuting || isJobRunning || isValidating}
                className="flex-1"
              >
                {isValidating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('services.execution.dryRun.validating')}
                  </>
                ) : (
                  <>
                    <Zap className="mr-2 h-4 w-4" />
                    {t('services.execution.dryRun.button')}
                  </>
                )}
              </Button>

              {/* Execute Button */}
              <Button
                type="submit"
                disabled={!file || !selectedFlavorId || isExecuting || isJobRunning || isValidating}
                className="flex-1"
              >
                {isExecuting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('services.execution.executing')}
                  </>
                ) : isJobRunning ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('services.execution.processing')}
                  </>
                ) : (
                  t('services.execution.execute')
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Fallback Applied Alert */}
      {fallbackInfo?.applied && (
        <Alert variant="default" className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
          <AlertTriangle className="h-4 w-4 text-yellow-600" />
          <AlertTitle className="text-yellow-800 dark:text-yellow-200">
            {t('services.execution.fallbackApplied')}
          </AlertTitle>
          <AlertDescription className="text-yellow-700 dark:text-yellow-300">
            <p>
              {t('services.execution.fallbackDetails', {
                original: fallbackInfo.originalFlavorName || '?',
                fallback: fallbackInfo.fallbackFlavorName || '?',
              })}
            </p>
            {fallbackInfo.inputTokens !== undefined && fallbackInfo.contextAvailable !== undefined && (
              <p className="text-sm mt-1">
                {t('services.execution.contextInfo', {
                  inputTokens: fallbackInfo.inputTokens,
                  contextAvailable: fallbackInfo.contextAvailable,
                })}
              </p>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Job Result - pass merged data from WebSocket + REST */}
      {jobId && (
        <JobResult
          job={jobStatus ? {
            ...jobStatus,
            status: currentStatus || jobStatus.status,
            progress: currentProgress,
            result: currentResult,
            error: currentError,
          } : currentStatus ? {
            // WebSocket-only data when REST hasn't loaded yet
            id: jobId,
            status: currentStatus,
            progress: currentProgress,
            result: currentResult,
            error: currentError,
          } as any : undefined}
          isLoading={isPolling}
        />
      )}

      {/* Synthetic Template Browser */}
      <SyntheticTemplateBrowser
        open={templateBrowserOpen}
        onOpenChange={setTemplateBrowserOpen}
        onSelect={handleTemplateSelect}
      />
    </div>
  );
}
