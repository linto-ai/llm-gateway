'use client';

import { use, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import { toast } from 'sonner';
import { Pencil, Trash2, Copy, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { PromptForm } from '@/components/prompts/PromptForm';

import { usePrompt, useDeletePrompt } from '@/hooks/use-prompts';

interface PageProps {
  params: Promise<{ locale: string; id: string }>;
}

export default function PromptDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { id, locale } = resolvedParams;
  const t = useTranslations('prompts');
  const tCommon = useTranslations('common');
  const router = useRouter();

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);

  // Fetch prompt data
  const { data: prompt, isLoading, error } = usePrompt(id);

  // Mutations
  const deletePrompt = useDeletePrompt();

  const handleDelete = async () => {
    try {
      await deletePrompt.mutateAsync(id);
      toast.success(t('deleteSuccess'));
      router.push(`/${locale}/prompts`);
    } catch (error: any) {
      toast.error(error.message || t('deleteError'));
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !prompt) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardHeader>
            <CardTitle>{tCommon('error')}</CardTitle>
            <CardDescription>
              {error?.message || 'Prompt not found'}
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/${locale}/prompts`}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              {tCommon('back')}
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{prompt.name}</h1>
            <div className="flex gap-2 mt-1">
              <Badge variant={prompt.organization_id ? 'default' : 'secondary'}>
                {prompt.organization_id ? t('organization') : t('global')}
              </Badge>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setDuplicateDialogOpen(true)}>
            <Copy className="h-4 w-4 mr-2" />
            {t('duplicate')}
          </Button>
          <Button variant="outline" onClick={() => setEditDialogOpen(true)}>
            <Pencil className="h-4 w-4 mr-2" />
            {tCommon('edit')}
          </Button>
          <Button variant="destructive" onClick={() => setDeleteDialogOpen(true)}>
            <Trash2 className="h-4 w-4 mr-2" />
            {tCommon('delete')}
          </Button>
        </div>
      </div>

      {/* Content */}
      <Card>
        <CardHeader>
          <CardTitle>{t('fields.content')}</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="whitespace-pre-wrap font-mono text-sm bg-muted p-4 rounded-md overflow-x-auto">
            {prompt.content}
          </pre>
        </CardContent>
      </Card>

      {/* Descriptions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{t('fields.descriptionEn')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap">{prompt.description.en}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('fields.descriptionFr')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap">{prompt.description.fr}</p>
          </CardContent>
        </Card>
      </div>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Metadata</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">
                {t('serviceType')}
              </h3>
              <Badge variant="default">{prompt.service_type}</Badge>
            </div>

            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">
                {t('fields.category')}
              </h3>
              <Badge variant={prompt.prompt_category === 'system' ? 'secondary' : 'outline'}>
                {prompt.prompt_category ? t(`category.${prompt.prompt_category}`) : '-'}
              </Badge>
            </div>

            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">
                {t('fields.promptType')}
              </h3>
              {prompt.prompt_type ? (
                <Badge variant="outline">
                  {prompt.prompt_type.name[locale as keyof typeof prompt.prompt_type.name] || prompt.prompt_type.code}
                </Badge>
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </div>

            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">
                {t('fields.organizationId')}
              </h3>
              <p className="font-mono text-sm">
                {prompt.organization_id || t('global')}
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">
                {tCommon('createdAt')}
              </h3>
              <p className="text-sm">
                {new Date(prompt.created_at).toLocaleString()}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">
                {tCommon('updatedAt')}
              </h3>
              <p className="text-sm">
                {new Date(prompt.updated_at).toLocaleString()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Edit Prompt Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('editPrompt')}</DialogTitle>
          </DialogHeader>
          <PromptForm
            prompt={prompt}
            onSuccess={() => {
              setEditDialogOpen(false);
              toast.success(t('updateSuccess'));
            }}
            onCancel={() => setEditDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Duplicate Prompt Dialog */}
      <Dialog open={duplicateDialogOpen} onOpenChange={setDuplicateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('duplicate')}</DialogTitle>
          </DialogHeader>
          <PromptForm
            prompt={prompt}
            duplicateMode={true}
            onSuccess={() => {
              setDuplicateDialogOpen(false);
              toast.success(t('duplicateSuccess'));
            }}
            onCancel={() => setDuplicateDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('deletePrompt')}
        description={`${t('deleteConfirm')} ${t('deleteWarning')}`}
        onConfirm={handleDelete}
        variant="destructive"
      />
    </div>
  );
}
