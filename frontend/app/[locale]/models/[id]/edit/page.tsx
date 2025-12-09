'use client';

import { use, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useModel, useUpdateModel } from '@/hooks/use-models';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { ModelForm } from '@/components/models/ModelForm';
import { ModelLimitsSection } from '@/components/models/ModelLimitsSection';
import { TokenizerSelector } from '@/components/models/TokenizerSelector';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import type { ModelResponse } from '@/types/model';

interface PageProps {
  params: Promise<{ locale: string; id: string }>;
}

export default function ModelEditPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { id, locale } = resolvedParams;
  const t = useTranslations();
  const router = useRouter();
  const updateModel = useUpdateModel();

  const { data: model, isLoading, error } = useModel(id);

  // Track limit values locally for editing
  const [limits, setLimits] = useState<{
    context_length: number;
    max_generation_length: number;
  }>({
    context_length: 0,
    max_generation_length: 0,
  });

  // Track tokenizer values locally for editing
  const [tokenizer, setTokenizer] = useState<{
    tokenizer_class: string | null;
    tokenizer_name: string | null;
  }>({
    tokenizer_class: null,
    tokenizer_name: null,
  });

  // Initialize limits and tokenizer from model when data arrives
  useEffect(() => {
    if (model) {
      setLimits({
        context_length: model.context_length,
        max_generation_length: model.max_generation_length,
      });
      setTokenizer({
        tokenizer_class: model.tokenizer_class,
        tokenizer_name: model.tokenizer_name,
      });
    }
  }, [model]);

  const handleLimitsChange = (field: string, value: number) => {
    setLimits(prev => ({ ...prev, [field]: value }));
  };

  const handleTokenizerChange = (tokenizerClass: string | null, tokenizerName: string | null) => {
    setTokenizer({
      tokenizer_class: tokenizerClass,
      tokenizer_name: tokenizerName,
    });
  };

  // Create a model object with updated limits for display
  const modelWithLimits: ModelResponse | undefined = model ? {
    ...model,
    context_length: limits.context_length,
    max_generation_length: limits.max_generation_length,
  } : undefined;

  // Handler to save limits and tokenizer when form is submitted
  const handleFormSuccess = async () => {
    // Check if limits have changed
    const limitsChanged =
      model && (
        limits.context_length !== model.context_length ||
        limits.max_generation_length !== model.max_generation_length
      );

    // Check if tokenizer has changed
    const tokenizerChanged =
      model && (
        tokenizer.tokenizer_class !== model.tokenizer_class ||
        tokenizer.tokenizer_name !== model.tokenizer_name
      );

    if ((limitsChanged || tokenizerChanged) && model) {
      try {
        const updateData: Record<string, any> = {};

        if (limitsChanged) {
          updateData.context_length = limits.context_length;
          updateData.max_generation_length = limits.max_generation_length;
        }

        if (tokenizerChanged) {
          updateData.tokenizer_class = tokenizer.tokenizer_class;
          updateData.tokenizer_name = tokenizer.tokenizer_name;
        }

        await updateModel.mutateAsync({
          id: model.id,
          data: updateData,
        });
      } catch (error: any) {
        toast.error(error.message || t('errors.generic'));
        return;
      }
    }

    router.push(`/${locale}/models/${id}`);
  };

  if (isLoading) return <LoadingSpinner />;
  if (error || !model || !modelWithLimits) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <p>{t('errors.notFound')}</p>
        <Button asChild>
          <Link href={`/${locale}/models`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common.back')}
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-2 text-sm text-muted-foreground">
        <Link href={`/${locale}/models`}>{t('nav.models')}</Link>
        <span>/</span>
        <Link href={`/${locale}/models/${id}`}>{model.model_name}</Link>
        <span>/</span>
        <span className="text-foreground">{t('common.edit')}</span>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('models.editModel')}</CardTitle>
        </CardHeader>
        <CardContent>
          <ModelForm
            model={model}
            locale={locale}
            onSuccess={handleFormSuccess}
            onCancel={() => router.back()}
          />
        </CardContent>
      </Card>

      {/* Token Limits Section - simplified */}
      <ModelLimitsSection
        model={modelWithLimits}
        onChange={handleLimitsChange}
      />

      {/* Tokenizer Section */}
      <TokenizerSelector
        tokenizerClass={tokenizer.tokenizer_class}
        tokenizerName={tokenizer.tokenizer_name}
        onChange={handleTokenizerChange}
      />
    </div>
  );
}
