'use client';

import { use } from 'react';
import { useRouter } from '@/lib/navigation';
import { useTranslations } from 'next-intl';
import { useModel, useDeleteModel, useVerifyModel } from '@/hooks/use-models';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { ModelHealthStatus } from '@/components/models/ModelHealthStatus';
import { toast } from 'sonner';
import { useState } from 'react';
import { Pencil, Trash2, ArrowLeft, Shield, ShieldAlert, ShieldOff } from 'lucide-react';
import { Link } from '@/lib/navigation';

interface PageProps {
  params: Promise<{ locale: string; id: string }>;
}

// Helper to map health_status to StatusBadge status
const getStatusBadgeType = (healthStatus: string): 'verified' | 'not-verified' | 'default' => {
  switch (healthStatus) {
    case 'available':
      return 'verified';
    case 'unavailable':
    case 'error':
      return 'not-verified';
    default:
      return 'default';
  }
};

// Format token count for display
const formatTokens = (count: number | undefined | null): string => {
  if (!count) return '-';
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
  if (count >= 1000) return `${(count / 1000).toFixed(0)}K`;
  return count.toLocaleString();
};

export default function ModelDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { id, locale } = resolvedParams;
  const t = useTranslations();
  const router = useRouter();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const { data: model, isLoading, error } = useModel(id);
  const deleteModel = useDeleteModel();
  const verifyModelMutation = useVerifyModel();

  const handleVerify = async () => {
    try {
      const result = await verifyModelMutation.mutateAsync(id);

      if (result.health_status === 'available') {
        toast.success(t('models.health.verificationSuccess'));
      } else if (result.health_status === 'unavailable') {
        toast.warning(result.error || t('models.health.modelUnavailable'));
      } else {
        toast.info(t('models.health.verificationComplete'));
      }
    } catch (error: any) {
      toast.error(error.message || t('models.health.verificationFailed'));
    }
  };

  const handleDelete = async () => {
    try {
      await deleteModel.mutateAsync(id);
      toast.success(t('models.deleteSuccess'));
      router.push('/models');
    } catch (error: any) {
      toast.error(error.message || t('models.deleteError'));
    }
  };

  if (isLoading) return <LoadingSpinner />;
  if (error || !model) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <p className="text-lg text-muted-foreground">{t('errors.notFound')}</p>
        <Button asChild>
          <Link href="/models">
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common.back')}
          </Link>
        </Button>
      </div>
    );
  }

  const availableForInput = model.context_length - model.max_generation_length;

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-2 text-sm text-muted-foreground">
        <Link href="/models" className="hover:text-foreground">
          {t('nav.models')}
        </Link>
        <span>/</span>
        <span className="text-foreground">{model.model_name}</span>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold font-mono">{model.model_name}</h1>
          <p className="text-muted-foreground mt-1">{model.model_identifier}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href={`/models/${id}/edit`}>
              <Pencil className="mr-2 h-4 w-4" />
              {t('common.edit')}
            </Link>
          </Button>
          <Button
            variant="destructive"
            onClick={() => setDeleteDialogOpen(true)}
            disabled={deleteModel.isPending}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            {t('common.delete')}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('models.viewModel')}</CardTitle>
          <CardDescription>{t('models.subtitle')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">{t('models.fields.name')}</p>
              <p className="text-base font-mono">{model.model_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">{t('models.fields.modelIdentifier')}</p>
              <p className="text-base">{model.model_identifier}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">{t('models.fields.healthStatus')}</p>
              <StatusBadge
                status={getStatusBadgeType(model.health_status)}
                label={model.health_status || t('models.notVerified')}
              />
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">{t('common.createdAt')}</p>
              <p className="text-base">{new Date(model.created_at).toLocaleString()}</p>
            </div>
          </div>
          {model.model_metadata && Object.keys(model.model_metadata).length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">{t('models.fields.metadata')}</p>
              <pre className="bg-muted p-3 rounded-md text-xs overflow-auto">
                {JSON.stringify(model.model_metadata, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Technical Specifications Card - Simplified */}
      <Card>
        <CardHeader>
          <CardTitle>{t('models.limits.title')}</CardTitle>
          <CardDescription>{t('models.limits.subtitle')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Token Limits - Show direct values */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">{t('models.limits.contextLength')}</p>
              <p className="text-2xl font-mono font-bold">{formatTokens(model.context_length)}</p>
              <p className="text-xs text-muted-foreground">tokens</p>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">{t('models.limits.maxGeneration')}</p>
              <p className="text-2xl font-mono font-bold">{formatTokens(model.max_generation_length)}</p>
              <p className="text-xs text-muted-foreground">tokens</p>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">{t('models.limits.availableForInput')}</p>
              <p className="text-2xl font-mono font-bold">{formatTokens(availableForInput)}</p>
              <p className="text-xs text-muted-foreground">tokens</p>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">{t('models.fields.tokenizer')}</p>
              <p className="text-lg font-mono">{model.tokenizer_name || model.tokenizer_class || '-'}</p>
            </div>
          </div>

          {/* Additional Technical Info */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-4 border-t">
            {model.huggingface_repo && (
              <div>
                <p className="text-xs text-muted-foreground">{t('models.fields.huggingfaceRepo')}</p>
                <a
                  href={`https://huggingface.co/${model.huggingface_repo}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-mono text-primary hover:underline"
                >
                  {model.huggingface_repo}
                </a>
              </div>
            )}
            {model.deployment_name && (
              <div>
                <p className="text-xs text-muted-foreground">{t('models.fields.deploymentName')}</p>
                <p className="text-sm font-mono">{model.deployment_name}</p>
              </div>
            )}
            {model.security_level && (
              <div>
                <p className="text-xs text-muted-foreground">{t('models.fields.securityLevel')}</p>
                <div className="flex items-center gap-1.5 mt-1">
                  {model.security_level === 'secure' && <Shield className="h-4 w-4 text-green-600" />}
                  {model.security_level === 'sensitive' && <ShieldAlert className="h-4 w-4 text-yellow-600" />}
                  {model.security_level === 'insecure' && <ShieldOff className="h-4 w-4 text-red-600" />}
                  <span className="text-sm">{t(`models.securityLevels.${model.security_level}`)}</span>
                </div>
              </div>
            )}
            {model.best_use && (
              <div>
                <p className="text-xs text-muted-foreground">{t('models.fields.bestUse')}</p>
                <p className="text-sm">{model.best_use}</p>
              </div>
            )}
            {model.usage_type && (
              <div>
                <p className="text-xs text-muted-foreground">{t('models.fields.usageType')}</p>
                <p className="text-sm">{model.usage_type}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Health Status Card */}
      <Card>
        <CardHeader>
          <CardTitle>{t('models.health.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <ModelHealthStatus
            model={model}
            onVerify={handleVerify}
            verifying={verifyModelMutation.isPending}
            locale={locale}
          />
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={handleDelete}
        title={t('models.deleteModel')}
        description={t('models.deleteWarning')}
        variant="destructive"
      />
    </div>
  );
}
